package com.example.demo.config;

import java.util.Set;


public final class PasswordPolicy {

    static final int MIN_LENGTH = 12;

    private static final Set<String> KNOWN_WEAK = Set.of(
            "analyst123", "admin123", "password", "password123", "changeme", "changeit", "123456789012");

    private PasswordPolicy() {}


    public static String require(String environmentVariable, String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(environmentVariable + " is not set. Set it to a password of at least "
                    + MIN_LENGTH + " characters before starting the backend.");
        }
        if (KNOWN_WEAK.contains(value.trim().toLowerCase())) {
            throw new IllegalStateException(environmentVariable + " is a well-known default password. Choose your own.");
        }
        if (value.length() < MIN_LENGTH) {
            throw new IllegalStateException(environmentVariable + " is too short: use at least "
                    + MIN_LENGTH + " characters.");
        }
        return value;
    }
}
