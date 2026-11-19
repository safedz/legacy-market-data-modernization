package com.example.demo.service;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;
@Service
public class DuckDbAnalyticsService {
    @Value("${pipeline.data-dir:../data}")
    private String dataDirectory;
    @Value("${analytics.script:../analytics/duckdb_analytics.py}")
    private String analyticsScript;
    @Value("${analytics.python-command:python}")
    private String pythonCommand;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();
    public JsonNode getSummary() {
        Path parquetFile = Path.of(dataDirectory)
                .resolve("lake")
                .resolve("curated")
                .resolve("validated_messages.parquet")
                .toAbsolutePath()
                .normalize();
        Path scriptFile = Path.of(analyticsScript)
                .toAbsolutePath()
                .normalize();
        if (!parquetFile.toFile().exists()) {
            throw new IllegalStateException("Curated Parquet file not found: " + parquetFile);
        }
        if (!scriptFile.toFile().exists()) {
            throw new IllegalStateException("DuckDB analytics script not found: " + scriptFile);
        }
        try {
            Process process = new ProcessBuilder(
                    pythonCommand,
                    scriptFile.toString(),
                    parquetFile.toString()
            ).start();
            boolean completed = process.waitFor(30, TimeUnit.SECONDS);
            if (!completed) {
                process.destroyForcibly();
                throw new IllegalStateException("DuckDB analytics timed out.");
            }
            String output = new String(
                    process.getInputStream().readAllBytes(),
                    StandardCharsets.UTF_8
            );
            String error = new String(
                    process.getErrorStream().readAllBytes(),
                    StandardCharsets.UTF_8
            );
            if (process.exitValue() != 0) {
                throw new IllegalStateException("DuckDB analytics failed: " + error);
            }
            return jsonMapper.readTree(output);
        } catch (IOException e) {
            throw new IllegalStateException("Could not execute DuckDB analytics: " + e.getMessage(), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("DuckDB analytics was interrupted.", e);
        }
    }
}
