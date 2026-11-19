package com.example.demo.controller;

import com.example.demo.dto.DataLakeFile;
import com.example.demo.dto.DataLakeQueryResult;
import com.example.demo.dto.DataLakeSummary;
import com.example.demo.service.DataLakeQueryService;
import jakarta.validation.constraints.Pattern;
import java.util.List;
import java.util.Map;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api/lake")
public class DataLakeController {

    private final DataLakeQueryService service;

    public DataLakeController(DataLakeQueryService service) {
        this.service = service;
    }

    @GetMapping("/summary")
    public DataLakeSummary summary() {
        return service.getSummary();
    }

    @GetMapping("/files")
    public List<DataLakeFile> files() {
        return service.listFiles();
    }

    @GetMapping("/queries")
    public List<Map<String, String>> queries() {
        return service.listQueries();
    }

    @GetMapping("/query/{name}")
    public DataLakeQueryResult query(
            @PathVariable @Pattern(regexp = "[a-z-]{1,40}", message = "invalid query name") String name) {
        return service.runQuery(name);
    }
}