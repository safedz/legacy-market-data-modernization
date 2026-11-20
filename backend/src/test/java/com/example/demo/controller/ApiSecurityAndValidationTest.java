package com.example.demo.controller;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;


@SpringBootTest(properties = {
        "app.security.analyst-password=test-only-analyst-pw",
        "app.security.admin-password=test-only-admin-pw"
})
@AutoConfigureMockMvc
class ApiSecurityAndValidationTest {

    private static final String ANALYST = basic("analyst", "test-only-analyst-pw");
    private static final String ADMIN = basic("admin", "test-only-admin-pw");

    @Autowired
    MockMvc mvc;

    private static String basic(String user, String password) {
        String raw = user + ":" + password;
        return "Basic " + Base64.getEncoder().encodeToString(raw.getBytes(StandardCharsets.UTF_8));
    }

    // ---------- authentication and authorisation ----------

    @ParameterizedTest
    @ValueSource(strings = {
            "/api/analytics/summary",
            "/api/pipeline/summary",
            "/api/pipeline/batches",
            "/api/quality",
            "/api/rejected-records",
            "/api/surveillance/alerts",
            "/api/trades",
            "/api/lineage/12345"
    })
    void requestsWithoutCredentialsAreRejected(String path) throws Exception {
        mvc.perform(get(path)).andExpect(status().isUnauthorized());
    }

    @Test
    void wrongPasswordIsRejected() throws Exception {
        mvc.perform(get("/api/analytics/summary").header("Authorization", basic("analyst", "not-the-password")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void unknownUserIsRejected() throws Exception {
        mvc.perform(get("/api/analytics/summary").header("Authorization", basic("mallory", "test-only-analyst-pw")))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void authenticatedUserCannotReachPathsOutsideTheApi() throws Exception {
        mvc.perform(get("/internal/anything").header("Authorization", ANALYST))
                .andExpect(status().isForbidden());
    }

    @Test
    void writeMethodsAreNotAllowedOnTheApi() throws Exception {
        mvc.perform(post("/api/analytics/summary").header("Authorization", ANALYST))
                .andExpect(status().isMethodNotAllowed());
    }

    @Test
    void adminAccountIsAcceptedToo() throws Exception {
        MvcResult result = mvc.perform(get("/api/analytics/summary").header("Authorization", ADMIN)).andReturn();
        int code = result.getResponse().getStatus();
        assertTrue(code == 200 || code == 503, "expected 200 or 503 but got " + code);
    }

    // ---------- analytics endpoint ----------

    @Test
    void analyticsSummaryReturnsDataOrServiceUnavailable() throws Exception {
        MvcResult result = mvc.perform(get("/api/analytics/summary").header("Authorization", ANALYST)).andReturn();
        int code = result.getResponse().getStatus();
        // 503 is the documented answer when the lake file is not there (clean CI checkout).
        assertTrue(List.of(200, 503).contains(code), "expected 200 or 503 but got " + code);
        if (code == 200) {
            mvc.perform(get("/api/analytics/summary").header("Authorization", ANALYST))
                    .andExpect(jsonPath("$.totalRecords").isNumber())
                    .andExpect(jsonPath("$.avgPrice").isNumber())
                    .andExpect(jsonPath("$.maxPrice").isNumber())
                    .andExpect(jsonPath("$.avgOrderSize").isNumber())
                    .andExpect(jsonPath("$.largestOrder").isNumber())
                    .andExpect(jsonPath("$.priceBuckets").isArray())
                    .andExpect(jsonPath("$.sizeBuckets").isArray());
        }
    }

    // ---------- input validation (rejected before any data is read) ----------

    @ParameterizedTest
    @ValueSource(strings = {"abc", "12a", "1%27%20OR%201=1", "123456789012345678901"})
    void lineageRejectsNonNumericOrTooLongOrderIds(String orderId) throws Exception {
        mvc.perform(get("/api/lineage/" + orderId).header("Authorization", ANALYST))
                .andExpect(status().isBadRequest());
    }

    @Test
    void tradesRejectsNonNumericOrderId() throws Exception {
        mvc.perform(get("/api/trades").param("orderId", "abc").header("Authorization", ANALYST))
                .andExpect(status().isBadRequest());
    }

    @Test
    void tradesRejectsMalformedEventType() throws Exception {
        mvc.perform(get("/api/trades").param("eventType", "submit; DROP TABLE x").header("Authorization", ANALYST))
                .andExpect(status().isBadRequest());
    }

    @Test
    void tradesRejectsMalformedFromDate() throws Exception {
        mvc.perform(get("/api/trades").param("from", "yesterday").header("Authorization", ANALYST))
                .andExpect(status().isBadRequest());
    }

    @Test
    void tradesRejectsMalformedToDate() throws Exception {
        mvc.perform(get("/api/trades").param("to", "21/06/2012").header("Authorization", ANALYST))
                .andExpect(status().isBadRequest());
    }
}