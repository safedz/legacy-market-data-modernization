package com.example.demo.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.example.demo.dto.DataLakeQueryResult;
import com.example.demo.dto.DataLakeSummary;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.Statement;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class DataLakeQueryServiceTest {

    @TempDir
    Path tempDir;

    private Path lakeDir;

    
    private DataLakeQueryService newService(Path lake) {
        return new DataLakeQueryService(
                lake.toString(),
                lake.resolve("curated").resolve("validated_messages.parquet").toString());
    }

    @BeforeEach
    void createTinyLake() throws Exception {
        lakeDir = tempDir.resolve("lake");
        Path curated = lakeDir.resolve("curated");
        Files.createDirectories(curated);
        Files.createDirectories(lakeDir.resolve("raw"));

        String parquet = curated.resolve("validated_messages.parquet")
                .toString().replace("\\", "/");

        try (Connection c = DriverManager.getConnection("jdbc:duckdb:");
             Statement s = c.createStatement()) {
            s.execute("COPY (SELECT * FROM (VALUES "
                    + "('SUBMIT'), ('SUBMIT'), ('SUBMIT'), ('DELETE')) t(event_label)) "
                    + "TO '" + parquet + "' (FORMAT PARQUET)");
        }
    }

    @Test
    void summaryCountsRecordsWhenLakeExists() {
        DataLakeSummary summary = newService(lakeDir).getSummary();

        assertThat(summary.available()).isTrue();
        assertThat(summary.curatedFiles()).isEqualTo(1);
        assertThat(summary.curatedRecords()).isEqualTo(4);
    }

    @Test
    void eventCountsQueryReturnsRows() {
        DataLakeQueryResult result = newService(lakeDir).runQuery("event-counts");

        assertThat(result.rows()).hasSize(2);
        assertThat(result.rows().get(0).get(0)).isEqualTo("SUBMIT");
    }

    @Test
    void summaryIsUnavailableWhenLakeMissing() {
        DataLakeQueryService service = newService(tempDir.resolve("does-not-exist"));

        assertThat(service.getSummary().available()).isFalse();
    }

    @Test
    void unknownQueryNameIsRejected() {
        assertThrows(RuntimeException.class,
                () -> newService(lakeDir).runQuery("no-such-query"));
    }
}