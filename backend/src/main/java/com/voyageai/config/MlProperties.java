package com.voyageai.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Adresse du service de recommandation Python (propriété ml.base-url). */
@ConfigurationProperties(prefix = "ml")
public record MlProperties(String baseUrl) {}
