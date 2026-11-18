package com.example.demo.dto;

public record DataLakeFile(
        String zone,        
        String name,       
        String batchId,     
        long sizeBytes,
        String modifiedAt) {
}