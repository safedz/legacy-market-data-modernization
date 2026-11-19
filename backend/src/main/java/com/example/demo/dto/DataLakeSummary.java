package com.example.demo.dto;

public record DataLakeSummary(
        long rawFiles,
        long curatedFiles,
        long totalBytes,
        long curatedRecords,  
        String curatedFile,    
        boolean available) {   
}