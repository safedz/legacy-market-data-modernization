package com.example.demo.service;

import com.example.demo.dto.PipelineBatch;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import java.sql.Timestamp;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.BadSqlGrammarException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "pipeline.source", havingValue = "db")
public class DbMarketData {

    private static final int MAX_ROWS = 1000;
    private static final int MAX_ROWS_FOR_ONE_ORDER = 10_000;

    private static final String[] LINEAGE_COLUMNS = {
        "source_file", "source_record_number", "batch_id", "file_sha256", "ingestion_timestamp",
        "transformations_applied", "pipeline_version", "transformed_at",
        "validation_status", "reject_reason", "final_destination", "validated_at"
    };

    private final JdbcTemplate jdbc;

    public DbMarketData(DataSource dataSource) {
        this.jdbc = new JdbcTemplate(dataSource);
    }

    public PipelineSummary getSummary() {
        try {
            List<PipelineSummary> rows = jdbc.query(
                    "SELECT source_records, loaded_records, rejected_records, reconciled, "
                            + "last_run::text AS last_run FROM v_pipeline_summary",
                    (rs, i) -> {
                        String lastRun = rs.getString("last_run");
                        return new PipelineSummary(
                                rs.getLong("source_records"),
                                rs.getLong("loaded_records"),
                                rs.getLong("rejected_records"),
                                rs.getBoolean("reconciled"),
                                lastRun == null ? "pipeline not run yet" : lastRun);
                    });
            return rows.isEmpty() ? new PipelineSummary(0, 0, 0, false, "pipeline not run yet") : rows.get(0);
        } catch (BadSqlGrammarException e) {
            return new PipelineSummary(0, 0, 0, false, "database not loaded yet");
        }
    }

    public List<RejectedRecord> getRejectedRecords() {
        return jdbc.query(
                "SELECT r.rejected_id, r.order_id, r.reject_reason, b.source_file, r.source_record_number "
                        + "FROM rejected_messages r JOIN import_batches b ON b.batch_id = r.batch_id "
                        + "ORDER BY r.rejected_id LIMIT ?",
                (rs, i) -> new RejectedRecord(
                        rs.getLong(1),
                        text(rs.getString(2)),
                        text(rs.getString(3)),
                        text(rs.getString(4)),
                        rs.getInt(5)),
                MAX_ROWS);
    }

    public List<SurveillanceAlert> getAlerts() {
        return jdbc.query(
                "SELECT alert_id, alert_type, order_id, severity, description, detected_at::text "
                        + "FROM surveillance_alerts "
                        + "ORDER BY CASE severity WHEN 'HIGH' THEN 0 WHEN 'MEDIUM' THEN 1 ELSE 2 END, "
                        + "detected_at, alert_id LIMIT ?",
                (rs, i) -> new SurveillanceAlert(
                        rs.getLong(1),
                        text(rs.getString(2)),
                        text(rs.getString(3)),
                        text(rs.getString(4)),
                        text(rs.getString(5)),
                        text(rs.getString(6))),
                MAX_ROWS);
    }

    public List<Trade> searchTrades(String orderId) {
        return searchTrades(orderId, null, null, null);
    }

    public List<Trade> searchTrades(String orderId, String eventType, String from, String to) {
        boolean hasOrder = orderId != null && !orderId.isBlank();
        Long id = hasOrder ? parseId(orderId) : null;
        if (hasOrder && id == null) {
            return List.of();
        }

        StringBuilder sql = new StringBuilder(
                "SELECT order_id, time_sec::text, event_label, size, price_dollars, direction "
                        + "FROM market_messages WHERE 1 = 1");
        List<Object> args = new ArrayList<>();

        if (hasOrder) {
            sql.append(" AND order_id = ?");
            args.add(id);
        }
        if (eventType != null && !eventType.isBlank()) {
            sql.append(" AND event_label = ?");
            args.add(eventType.trim());
        }
        Timestamp fromTs = toTimestamp(from);
        if (fromTs != null) {
            sql.append(" AND event_timestamp >= ?");
            args.add(fromTs);
        }
        Timestamp toTs = toTimestamp(to);
        if (toTs != null) {
            sql.append(" AND event_timestamp <= ?");
            args.add(toTs);
        }

        sql.append(" ORDER BY batch_id, source_record_number LIMIT ?");
        args.add(hasOrder ? MAX_ROWS_FOR_ONE_ORDER : MAX_ROWS);

        return jdbc.query(sql.toString(),
                (rs, i) -> new Trade(
                        text(rs.getString(1)),
                        text(rs.getString(2)),
                        text(rs.getString(3)),
                        rs.getInt(4),
                        rs.getDouble(5),
                        rs.getInt(6) == 1 ? "BUY" : "SELL"),
                args.toArray());
    }

    private static Timestamp toTimestamp(String text) {
        if (text == null || text.isBlank()) {
            return null;
        }
        String s = text.trim().replace('T', ' ');
        if (s.length() == 10) {
            s += " 00:00:00";
        } else if (s.length() == 16) {
            s += ":00";
        }
        try {
            return Timestamp.valueOf(s);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }

    public List<PipelineBatch> getBatches() {
        return jdbc.query(
                "SELECT batch_id, source_file, trading_date::text, file_sha256, pipeline_version, "
                        + "ingestion_timestamp::text, source_records, loaded_records, rejected_records "
                        + "FROM import_batches ORDER BY ingestion_timestamp DESC",
                (rs, i) -> new PipelineBatch(
                        text(rs.getString(1)),
                        text(rs.getString(2)),
                        text(rs.getString(3)),
                        text(rs.getString(4)),
                        text(rs.getString(5)),
                        text(rs.getString(6)),
                        rs.getInt(7),
                        rs.getInt(8),
                        rs.getInt(9)));
    }

    public Map<String, String> lineageRow(String orderId) {
        Long id = parseId(orderId);
        if (id == null) {
            return null;
        }
        List<Map<String, String>> rows = jdbc.query(
                "SELECT source_file, source_record_number::text AS source_record_number, batch_id, file_sha256, "
                        + "ingestion_timestamp::text AS ingestion_timestamp, transformations_applied, "
                        + "pipeline_version, transformed_at::text AS transformed_at, validation_status, "
                        + "reject_reason, final_destination, validated_at::text AS validated_at "
                        + "FROM staging_messages WHERE order_id = ? "
                        + "ORDER BY (validation_status = 'VALID') DESC, source_record_number LIMIT 1",
                (rs, i) -> {
                    Map<String, String> row = new HashMap<>();
                    for (String column : LINEAGE_COLUMNS) {
                        row.put(column, text(rs.getString(column)));
                    }
                    return row;
                },
                id);
        return rows.isEmpty() ? null : rows.get(0);
    }

    private static Long parseId(String text) {
        try {
            return Long.parseLong(text.trim());
        } catch (NumberFormatException e) {
            return null; // longer than a long: no such order
        }
    }

    private static String text(String value) {
        return value == null ? "" : value;
    }
}