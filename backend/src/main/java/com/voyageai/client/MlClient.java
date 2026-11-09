package com.voyageai.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.voyageai.config.MlProperties;
import com.voyageai.dto.ItineraryRequest;
import com.voyageai.dto.RecommendRequest;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Client HTTP du service de recommandation Python. Les réponses sont relayées telles quelles. */
@Component
public class MlClient {

    private final RestClient client;

    public MlClient(MlProperties props, RestClient.Builder builder) {
        this.client = builder.baseUrl(props.baseUrl()).build();
    }

    public JsonNode meta() {
        return client.get().uri("/meta").retrieve().body(JsonNode.class);
    }

    public JsonNode recommend(RecommendRequest request) {
        return client.post().uri("/recommend")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(JsonNode.class);
    }

    public JsonNode itinerary(ItineraryRequest request) {
        return client.post().uri("/itinerary")
                .contentType(MediaType.APPLICATION_JSON)
                .body(request)
                .retrieve()
                .body(JsonNode.class);
    }

    public JsonNode place(long placeId) {
        return client.get().uri("/places/{id}", placeId).retrieve().body(JsonNode.class);
    }
}
