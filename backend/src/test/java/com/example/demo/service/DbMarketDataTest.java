package com.example.demo.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.example.demo.dto.PipelineSummary;
import com.example.demo.dto.SurveillanceAlert;
import com.example.demo.dto.Trade;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.jdbc.datasource.DriverManagerDataSource;


@EnabledIfEnvironmentVariable(named = "PEARL_TEST_JDBC_URL", matches = ".+")
class DbMarketDataTest {

    private static MarketDataService service;

    @BeforeAll
    static void connect() {
        DriverManagerDataSource ds = new DriverManagerDataSource(
                System.getenv("PEARL_TEST_JDBC_URL"),
                System.getenv().getOrDefault("PEARL_TEST_DB_USER", "surveillance_user"),
                System.getenv().getOrDefault("PEARL_TEST_DB_PASSWORD", ""));
        service = new MarketDataService("unused", Optional.of(new DbMarketData(ds)));
    }

    @Test
    void summaryReconciles() {
        PipelineSummary s = service.getSummary();
        assertTrue(s.sourceRecords() > 0);
        assertEquals(s.sourceRecords(), s.loadedRecords() + s.rejectedRecords());
        assertTrue(s.reconciled());
    }

    @Test
    void alertsComeFromTheDatabaseMostSevereFirst() {
        List<SurveillanceAlert> alerts = service.getAlerts();
        assertFalse(alerts.isEmpty());
        assertEquals("HIGH", alerts.get(0).severity());
        assertTrue(alerts.size() <= 1000);
    }

    @Test
    void tradesAndLineageForAnAlertedOrder() {
        String orderId = service.getAlerts().get(0).orderId();
        List<Trade> trades = service.searchTrades(orderId);
        assertFalse(trades.isEmpty());
        assertTrue(trades.stream().allMatch(t -> t.orderId().equals(orderId)));
        assertEquals(4, service.getLineage(orderId).size());
    }

    @Test
    void allTradesAreCapped() {
        assertEquals(1000, service.searchTrades(null).size());
    }

    @Test
    void unknownOrOversizedOrderIdGivesEmptyResults() {
        assertTrue(service.searchTrades("99999999999999999999").isEmpty());
        assertTrue(service.getLineage("99999999999999999999").isEmpty());
        assertTrue(service.getLineage("1").isEmpty());
    }
}