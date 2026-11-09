package com.voyageai;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class VoyageAiApplication {
    public static void main(String[] args) {
        SpringApplication.run(VoyageAiApplication.class, args);
    }
}
