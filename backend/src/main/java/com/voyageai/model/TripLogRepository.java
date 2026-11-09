package com.voyageai.model;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface TripLogRepository extends JpaRepository<TripLog, Long> {
    List<TripLog> findTop20ByOrderByCreatedAtDesc();
}
