package com.example.demo.service;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Reads the Python pipeline output (CSV / JSON) from the data folder.
 *
 * Temporary bridge until the PostgreSQL layer is ready: when the database
 * exists, only the read methods below need to change.
 *
 * Files are read on each request (never in the constructor), so the app
 * still starts, and tests still pass, when the pipeline has not been run.
 */
@Service
public class MarketDataService {

    private static final int MAX_ROWS = 1000;

    private final Path processedDir;
    private final Path rejectedFile;
    private final ObjectMapper mapper = new ObjectMapper();

    // Still sample data: surveillance queries need the database (Aweega's part)
    private final List<SurveillanceAlert> alerts = List.of(
            new SurveillanceAlert(1, "SPOOFING", "16135792", "HIGH",
                    "Large order cancelled within 1 ms of submission", "2026-10-25T09:30:01"),
            new SurveillanceAlert(2, "RAPID_CANCEL", "16140001", "MEDIUM",
                    "Repeated submit/cancel pattern detected", "2026-10-25T09:30:05"));

    public MarketDataService(@Value("${pipeline.data-dir:../data}") String dataDir) {
        Path base = Path.of(dataDir);
        this.processedDir = base.resolve("processed");
        this.rejectedFile = base.resolve("rejected").resolve("rejected_messages.csv");
    }

    public PipelineSummary getSummary() {
        Path file = processedDir.resolve("validation_report.json");
        if (!Files.exists(file)) {
            return new PipelineSummary(0, 0, 0, false, "pipeline not run yet");
        }
        try {
            JsonNode report = mapper.readTree(file.toFile());
            JsonNode stages = report.path("stages");
            long source = stages.path("ingested").path("records").asLong();
            long loaded = stages.path("valid").path("records").asLong();
            long rejectedCount = stages.path("rejected").path("records").asLong();
            boolean reconciled = report.path("reconciliation_pass").asBoolean();
            return new PipelineSummary(source, loaded, rejectedCount, reconciled,
                    report.path("validated_at").asText());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public List<RejectedRecord> getRejectedRecords() {
        List<RejectedRecord> result = new ArrayList<>();
        int id = 1;
        for (Map<String, String> row : readCsv(rejectedFile, null, null, MAX_ROWS)) {
            result.add(new RejectedRecord(id++,
                    wholeNumber(row.get("order_id")),
                    value(row, "reject_reason"),
                    value(row, "source_file"),
                    toInt(row.get("source_record_number"))));
        }
        return result;
    }

    public List<SurveillanceAlert> getAlerts() {
        return alerts;
    }

    public List<Trade> searchTrades(String orderId) {
        boolean all = orderId == null || orderId.isBlank();
        List<Map<String, String>> rows = all
                ? readCsv(validatedFile(), null, null, MAX_ROWS)
                : readCsv(validatedFile(), "order_id", orderId.trim(), 10 * MAX_ROWS);
        List<Trade> result = new ArrayList<>();
        for (Map<String, String> row : rows) {
            result.add(toTrade(row));
        }
        return result;
    }

    public List<LineageStep> getLineage(String orderId) {
        Map<String, String> row = firstRow(validatedFile(), orderId);
        if (row == null) {
            row = firstRow(rejectedFile, orderId);
        }
        if (row == null) {
            return List.of();
        }
        boolean valid = "VALID".equals(row.get("validation_status"));
        String status = valid ? "OK" : "REJECTED";
        String hash = value(row, "file_sha256");
        String shortHash = hash.length() > 12 ? hash.substring(0, 12) : hash;

        return List.of(
                new LineageStep(1, "INGEST",
                        "Read " + value(row, "source_file") + " row " + value(row, "source_record_number")
                                + " (batch " + value(row, "batch_id") + ", SHA-256 " + shortHash + ")",
                        "OK", value(row, "ingestion_timestamp")),
                new LineageStep(2, "TRANSFORM",
                        "Applied " + value(row, "transformations_applied")
                                + " (pipeline v" + value(row, "pipeline_version") + ")",
                        "OK", value(row, "transformed_at")),
                new LineageStep(3, "VALIDATE",
                        valid ? "Passed all validation rules" : "Rejected: " + value(row, "reject_reason"),
                        status, value(row, "validated_at")),
                new LineageStep(4, "LOAD",
                        "Written to " + value(row, "final_destination") + " zone",
                        status, value(row, "validated_at")));
    }

    // ---- helpers ---------------------------------------------------------

    private Path validatedFile() {
        return processedDir.resolve("validated_messages.csv");
    }

    private Map<String, String> firstRow(Path file, String orderId) {
        if (orderId == null || orderId.isBlank()) {
            return null;
        }
        List<Map<String, String>> rows = readCsv(file, "order_id", orderId.trim(), 1);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private Trade toTrade(Map<String, String> row) {
        String side = "1".equals(wholeNumber(row.get("direction"))) ? "BUY" : "SELL";
        return new Trade(
                wholeNumber(row.get("order_id")),
                value(row, "time"),
                value(row, "event_label"),
                toInt(row.get("size")),
                Double.parseDouble(value(row, "price_dollars")),
                side);
    }

    /**
     * Streams a CSV file (the pipeline writes plain comma-separated values).
     * If filterColumn is given, only rows whose value equals filterValue are kept.
     */
    private List<Map<String, String>> readCsv(Path file, String filterColumn, String filterValue, int limit) {
        List<Map<String, String>> rows = new ArrayList<>();
        if (!Files.exists(file)) {
            return rows;
        }
        try (BufferedReader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            String headerLine = reader.readLine();
            if (headerLine == null) {
                return rows;
            }
            String[] header = headerLine.split(",", -1);

            int filterIndex = -1;
            if (filterColumn != null) {
                for (int i = 0; i < header.length; i++) {
                    if (header[i].equals(filterColumn)) {
                        filterIndex = i;
                    }
                }
                if (filterIndex < 0) {
                    return rows;
                }
            }

            String line;
            while (rows.size() < limit && (line = reader.readLine()) != null) {
                if (line.isBlank()) {
                    continue;
                }
                String[] cells = line.split(",", -1);
                if (cells.length != header.length) {
                    throw new IllegalStateException("Malformed CSV row in " + file);
                }
                if (filterIndex >= 0 && !wholeNumber(cells[filterIndex]).equals(filterValue)) {
                    continue;
                }
                Map<String, String> row = new HashMap<>();
                for (int i = 0; i < header.length; i++) {
                    row.put(header[i], cells[i]);
                }
                rows.add(row);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return rows;
    }

    private static String value(Map<String, String> row, String key) {
        String v = row.get(key);
        return v == null ? "" : v;
    }

    /** "16113575.0" -> "16113575" (pandas writes floats if a column had gaps). */
    private static String wholeNumber(String text) {
        String s = text == null ? "" : text.trim();
        return s.endsWith(".0") ? s.substring(0, s.length() - 2) : s;
    }

    private static int toInt(String text) {
        String s = wholeNumber(text);
        return s.isEmpty() ? 0 : Integer.parseInt(s);
    }
}
