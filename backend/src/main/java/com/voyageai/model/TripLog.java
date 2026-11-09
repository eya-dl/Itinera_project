package com.voyageai.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/** Trace d'une demande (recommandation ou itinéraire) pour l'historique et l'analyse d'usage. */
@Entity
@Table(name = "trip_log")
public class TripLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private Instant createdAt = Instant.now();

    private String type;

    private String city;

    @Column(length = 4000)
    private String payload;

    protected TripLog() {}

    public TripLog(String type, String city, String payload) {
        this.type = type;
        this.city = city;
        this.payload = payload;
    }

    public Long getId() { return id; }
    public Instant getCreatedAt() { return createdAt; }
    public String getType() { return type; }
    public String getCity() { return city; }
    public String getPayload() { return payload; }
}
