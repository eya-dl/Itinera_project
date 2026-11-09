package com.voyageai.web;

import com.fasterxml.jackson.databind.JsonNode;
import com.voyageai.client.MlClient;
import com.voyageai.dto.ItineraryRequest;
import com.voyageai.dto.RecommendRequest;
import com.voyageai.model.TripLog;
import com.voyageai.service.HistoryService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api")
public class TravelController {

    private final MlClient ml;
    private final HistoryService history;

    public TravelController(MlClient ml, HistoryService history) {
        this.ml = ml;
        this.history = history;
    }

    /** Villes et catégories disponibles (alimente les formulaires du frontend). */
    @GetMapping("/meta")
    public JsonNode meta() {
        return ml.meta();
    }

    @PostMapping("/recommendations")
    public JsonNode recommendations(@Valid @RequestBody RecommendRequest request) {
        JsonNode result = ml.recommend(request);
        history.record("recommendation", request.city(), request);
        return result;
    }

    @PostMapping("/itineraries")
    public JsonNode itineraries(@Valid @RequestBody ItineraryRequest request) {
        JsonNode result = ml.itinerary(request);
        history.record("itinerary", request.city(), request);
        return result;
    }

    @GetMapping("/places/{id}")
    public JsonNode place(@PathVariable long id) {
        return ml.place(id);
    }

    @GetMapping("/history")
    public List<TripLog> history() {
        return history.latest();
    }
}
