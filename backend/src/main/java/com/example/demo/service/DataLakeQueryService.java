package com.example.demo.service;

import com.example.demo.dto.DataLakeFile;
import com.example.demo.dto.DataLakeQueryResult;
import com.example.demo.dto.DataLakeSummary;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class DataLakeQueryService {

    private record NamedQuery(String description, String sql) {}

    // Browser එකෙන් SQL එන්නේ නෑ. මේ list එකේ තියෙන නම් විතරයි run වෙන්නේ.
    private static final Map<String, NamedQuery> QUERIES = new LinkedHashMap<>();
    static {
        QUERIES.put("event-counts", new NamedQuery("Messages per event type",
                "SELECT event_label, count(*) AS messages FROM read_parquet('%s') GROUP BY 1 ORDER BY 2 DESC"));
        QUERIES.put("price-range", new NamedQuery("Minimum, maximum and average price",
                "SELECT min(price_dollars) AS min_price, max(price_dollars) AS max_price, "
                        + "avg(price_dollars) AS avg_price FROM read_parquet('%s')"));
        QUERIES.put("top-orders", new NamedQuery("20 orders with the most messages",
                "SELECT order_id, count(*) AS messages FROM read_parquet('%s') "
                        + "GROUP BY 1 ORDER BY 2 DESC LIMIT 20"));
        QUERIES.put("duplicates", new NamedQuery("Duplicate versus unique messages",
                "SELECT is_duplicate, count(*) AS messages FROM read_parquet('%s') GROUP BY 1"));
    }

    private final Path lakeDir;
    private final Path curatedFile;

    public DataLakeQueryService(@Value("${lake.dir:../data/lake}") String lakeDir,
                                @Value("${lake.curated-file:../data/lake/curated/validated_messages.parquet}") String curatedFile) {
        this.lakeDir = Path.of(lakeDir);
        this.curatedFile = Path.of(curatedFile);
    }

    public List<DataLakeFile> listFiles() {
        List<DataLakeFile> files = new ArrayList<>();
        for (String zone : List.of("raw", "curated")) {
            Path zoneDir = lakeDir.resolve(zone);
            if (!Files.isDirectory(zoneDir)) {
                continue;
            }
            try (Stream<Path> walk = Files.walk(zoneDir)) {
                for (Path p : (Iterable<Path>) walk.filter(Files::isRegularFile)::iterator) {
                    if (p.getFileName().toString().equals(".gitkeep")) {
                        continue;
                    }
                    Path relative = zoneDir.relativize(p);
                    String batchId = relative.getNameCount() > 1 ? relative.getName(0).toString() : "";
                    files.add(new DataLakeFile(zone, p.getFileName().toString(), batchId,
                            Files.size(p), Files.getLastModifiedTime(p).toInstant().toString()));
                }
            } catch (IOException e) {
                throw new UncheckedIOException("Cannot read " + zoneDir, e);
            }
        }
        return files;
    }

    public DataLakeSummary getSummary() {
        List<DataLakeFile> files = listFiles();
        long raw = files.stream().filter(f -> f.zone().equals("raw")).count();
        long curated = files.stream().filter(f -> f.zone().equals("curated")).count();
        long bytes = files.stream().mapToLong(DataLakeFile::sizeBytes).sum();
        boolean available = Files.exists(curatedFile);
        long records = available ? countRecords() : 0;
        return new DataLakeSummary(raw, curated, bytes, records, curatedFile.toString(), available);
    }

    public List<Map<String, String>> listQueries() {
        List<Map<String, String>> list = new ArrayList<>();
        QUERIES.forEach((name, q) -> list.add(Map.of("name", name, "description", q.description())));
        return list;
    }

    public DataLakeQueryResult runQuery(String name) {
        NamedQuery query = QUERIES.get(name);
        if (query == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Unknown query: " + name);
        }
        if (!Files.exists(curatedFile)) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "Data lake not available yet. Run the pipeline first.");
        }
        try (Connection c = DriverManager.getConnection("jdbc:duckdb:");
             Statement s = c.createStatement();
             ResultSet rs = s.executeQuery(query.sql().formatted(sqlPath()))) {
            ResultSetMetaData md = rs.getMetaData();
            List<String> columns = new ArrayList<>();
            for (int i = 1; i <= md.getColumnCount(); i++) {
                columns.add(md.getColumnLabel(i));
            }
            List<List<Object>> rows = new ArrayList<>();
            while (rs.next()) {
                List<Object> row = new ArrayList<>();
                for (int i = 1; i <= columns.size(); i++) {
                    row.add(rs.getObject(i));
                }
                rows.add(row);
            }
            return new DataLakeQueryResult(name, query.description(), columns, rows);
        } catch (SQLException e) {
            throw new IllegalStateException("DuckDB query failed: " + name, e);
        }
    }

    private long countRecords() {
        try (Connection c = DriverManager.getConnection("jdbc:duckdb:");
             Statement s = c.createStatement();
             ResultSet rs = s.executeQuery("SELECT count(*) FROM read_parquet('" + sqlPath() + "')")) {
            rs.next();
            return rs.getLong(1);
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot count records in " + curatedFile, e);
        }
    }

   
    private String sqlPath() {
        return curatedFile.toAbsolutePath().normalize().toString()
                .replace("\\", "/").replace("'", "''");
    }
}