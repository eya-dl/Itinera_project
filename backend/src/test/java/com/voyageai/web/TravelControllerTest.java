package com.voyageai.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.voyageai.client.MlClient;
import com.voyageai.service.HistoryService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.ResourceAccessException;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(TravelController.class)
class TravelControllerTest {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @MockBean MlClient ml;
    @MockBean HistoryService history;

    @Test
    void recommendationsRelaysMlPayload() throws Exception {
        when(ml.recommend(any())).thenReturn(mapper.readTree("{\"count\":1,\"items\":[{\"name\":\"Monas\"}]}"));

        mvc.perform(post("/api/recommendations")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"city\":\"Jakarta\",\"interests\":{\"culture\":5},\"budget_eur\":20}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.count").value(1))
                .andExpect(jsonPath("$.items[0].name").value("Monas"));
    }

    @Test
    void invalidInterestWeightIsRejected() throws Exception {
        mvc.perform(post("/api/recommendations")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"interests\":{\"culture\":9}}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("validation"));
    }

    @Test
    void itineraryRequiresCity() throws Exception {
        mvc.perform(post("/api/itineraries")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"days\":2}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void mlServiceDownReturns503() throws Exception {
        when(ml.recommend(any())).thenThrow(new ResourceAccessException("connection refused"));

        mvc.perform(post("/api/recommendations")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error").value("ml_service_unavailable"));
    }
}
