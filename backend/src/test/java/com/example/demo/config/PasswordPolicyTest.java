package com.example.demo.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Test;

class PasswordPolicyTest {

    @Test
    void acceptsALongEnoughPassword() {
        assertEquals("correct-horse-battery", PasswordPolicy.require("ANALYST_PASSWORD", "correct-horse-battery"));
    }

    @Test
    void rejectsMissingOrBlankPasswords() {
        IllegalStateException e = assertThrows(IllegalStateException.class,
                () -> PasswordPolicy.require("ANALYST_PASSWORD", ""));
        assertTrue(e.getMessage().contains("ANALYST_PASSWORD is not set"));
        assertThrows(IllegalStateException.class, () -> PasswordPolicy.require("ADMIN_PASSWORD", null));
        assertThrows(IllegalStateException.class, () -> PasswordPolicy.require("ADMIN_PASSWORD", "   "));
    }

    @Test
    void rejectsTheOldDefaultsWhateverTheCase() {
        assertThrows(IllegalStateException.class, () -> PasswordPolicy.require("ANALYST_PASSWORD", "analyst123"));
        assertThrows(IllegalStateException.class, () -> PasswordPolicy.require("ADMIN_PASSWORD", "Admin123"));
    }

    @Test
    void rejectsShortPasswords() {
        IllegalStateException e = assertThrows(IllegalStateException.class,
                () -> PasswordPolicy.require("ADMIN_PASSWORD", "short-pw-1"));
        assertTrue(e.getMessage().contains("too short"));
    }

    @Test
    void theTestPasswordsUsedByTheBuildPassThePolicy() {
        PasswordPolicy.require("ANALYST_PASSWORD", "test-only-analyst-pw");
        PasswordPolicy.require("ADMIN_PASSWORD", "test-only-admin-pw");
    }
}
