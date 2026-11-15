package com.example.demo.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.example.demo.dto.LineageStep;
import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.QualityReport;
import com.example.demo.dto.RejectedRecord;
import com.example.demo.dto.Trade;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;


class MarketDataServiceCsvTest {

    private static final String VALID_HEADER = "source_record_number,time,event_type,order_id,size,price,direction,"
            + "source_file,trading_date,file_sha256,batch_id,ingestion_timestamp,price_dollars,event_timestamp,"
            + "event_label,is_duplicate,pipeline_version,transformations_applied,transformed_at,reject_reason,"
            + "validation_status,final_destination,validated_at";

    private static String row(int record, String orderId, String status, String reason, String dest) {
        return record + ",34200.5,1," + orderId + ",10,5853300,1,f.csv,2012-06-21,abcdef0123456789abcd,B1,"
                + "2026-01-01T00:00:00,585.33,2012-06-21 09:30:00.5,SUBMIT,False,1.0.0,trim,"
                + "2026-01-01T00:00:01," + reason + "," + status + "," + dest + ",2026-01-01T00:00:02";
    }

    private MarketDataService service(Path dir) {
        return new MarketDataService(dir.toString(), Optional.empty());
    }

    private void write(Path file, String... lines) throws IOException {
        Files.createDirectories(file.getParent());
        Files.write(file, List.of(lines), StandardCharsets.UTF_8);
    }

    @Test
    void summaryWhenPipelineNotRun(@TempDir Path dir) {
        PipelineSummary s = service(dir).getSummary();
        assertFalse(s.reconciled());
        assertEquals("pipeline not run yet", s.lastRun());
    }

    @Test
    void summaryReadsValidationReport(@TempDir Path dir) throws IOException {
        write(dir.resolve("processed/validation_report.json"),
                "{\"validated_at\":\"t\",\"reconciliation_pass\":true,\"stages\":{\"ingested\":{\"records\":5},"
                        + "\"valid\":{\"records\":4},\"rejected\":{\"records\":1}}}");
        PipelineSummary s = service(dir).getSummary();
        assertEquals(5, s.sourceRecords());
        assertEquals(4, s.loadedRecords());
        assertEquals(1, s.rejectedRecords());
        assertTrue(s.reconciled());
    }

    @Test
    void tradesAreFilteredByOrderId(@TempDir Path dir) throws IOException {
        write(dir.resolve("processed/validated_messages.csv"), VALID_HEADER,
                row(1, "111", "VALID", "", "curated"), row(2, "222.0", "VALID", "", "curated"));
        MarketDataService service = service(dir);
        assertEquals(2, service.searchTrades(null).size());
        List<Trade> one = service.searchTrades("222");
        assertEquals(1, one.size());
        assertEquals("222", one.get(0).orderId());
        assertEquals("BUY", one.get(0).direction());
        assertEquals(585.33, one.get(0).price(), 1e-9);
    }

    @Test
    void rejectedRecordsAreListed(@TempDir Path dir) throws IOException {
        write(dir.resolve("rejected/rejected_messages.csv"), VALID_HEADER,
                row(7, "333", "REJECTED", "INVALID_SIZE", "rejected"));
        List<RejectedRecord> rejected = service(dir).getRejectedRecords();
        assertEquals(1, rejected.size());
        assertEquals("INVALID_SIZE", rejected.get(0).reason());
        assertEquals(7, rejected.get(0).lineNumber());
    }

    @Test
    void lineageForValidAndRejectedOrders(@TempDir Path dir) throws IOException {
        write(dir.resolve("processed/validated_messages.csv"), VALID_HEADER,
                row(1, "111", "VALID", "", "curated"));
        write(dir.resolve("rejected/rejected_messages.csv"), VALID_HEADER,
                row(7, "333", "REJECTED", "INVALID_SIZE", "rejected"));
        MarketDataService service = service(dir);

        List<LineageStep> ok = service.getLineage("111");
        assertEquals(4, ok.size());
        assertEquals("OK", ok.get(2).status());

        List<LineageStep> bad = service.getLineage("333");
        assertEquals("REJECTED", bad.get(2).status());
        assertTrue(bad.get(2).description().contains("INVALID_SIZE"));

        assertTrue(service.getLineage("999").isEmpty());
    }

    @Test
    void qualityWhenNotRun(@TempDir Path dir) {
        QualityReport q = service(dir).getQuality();
        assertEquals("NOT_RUN", q.orderBookStatus());
        assertFalse(q.overallPass());
    }

    @Test
    void qualityReadsReport(@TempDir Path dir) throws IOException {
        write(dir.resolve("processed/quality_report.json"),
                "{\"batch_id\":\"B1\",\"generated_at\":\"t\",\"overall_pass\":true,"
                        + "\"orderbook_reconciliation\":{\"status\":\"PASS\",\"checked\":10,\"matched\":10,"
                        + "\"mismatched\":0,\"match_rate\":1.0,\"coverage\":0.9},"
                        + "\"order_lifecycle\":{\"pass\":true,\"orphan_events\":3,"
                        + "\"violations\":{\"time_regressions\":0,\"duplicate_submits\":0}}}");
        QualityReport q = service(dir).getQuality();
        assertEquals("PASS", q.orderBookStatus());
        assertEquals(10, q.checked());
        assertEquals(3, q.orphanEvents());
        assertEquals(2, q.lifecycleViolations().size());
        assertTrue(q.overallPass());
    }

    @Test
    void csvModeStillServesSampleAlerts(@TempDir Path dir) {
        assertFalse(service(dir).getAlerts().isEmpty());
    }
}