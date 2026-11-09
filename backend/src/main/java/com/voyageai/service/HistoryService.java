package com.voyageai.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.voyageai.model.TripLog;
import com.voyageai.model.TripLogRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class HistoryService {

    private final TripLogRepository repository;
    private final ObjectMapper mapper;

    public HistoryService(TripLogRepository repository, ObjectMapper mapper) {
        this.repository = repository;
        this.mapper = mapper;
    }

    /** L'historique ne doit jamais faire échouer une recommandation : les erreurs sont ignorées. */
    public void record(String type, String city, Object request) {
        try {
            String json = mapper.writeValueAsString(request);
            String payload = json.length() > 4000 ? json.substring(0, 4000) : json;
            repository.save(new TripLog(type, city, payload));
        } catch (JsonProcessingException | RuntimeException ignored) {
            // volontairement silencieux
        }
    }

    public List<TripLog> latest() {
        return repository.findTop20ByOrderByCreatedAtDesc();
    }
}
