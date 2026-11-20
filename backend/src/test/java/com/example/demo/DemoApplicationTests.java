package com.example.demo;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
@SpringBootTest(properties = {
        "app.security.analyst-password=test-only-analyst-pw",
        "app.security.admin-password=test-only-admin-pw"
})
class DemoApplicationTests {
    @Test
    void contextLoads() {
    }
}