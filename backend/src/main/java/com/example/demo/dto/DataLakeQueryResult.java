package com.example.demo.dto;

import java.util.List;

public record DataLakeQueryResult(
        String name,                 
        String description,
        List<String> columns,        
        List<List<Object>> rows) {   
}