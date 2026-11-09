package com.voyageai.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;

import java.util.List;
import java.util.Map;

/**
 * Profil du voyageur pour la recommandation de lieux.
 * Le budget couvre les entrées des lieux, par personne, pour tout le séjour.
 */
public record RecommendRequest(
        String city,
        Map<@Pattern(regexp = "sea|culture|nature|amusement|shopping|religious") String,
                @Min(0) @Max(5) Integer> interests,
        @Positive Double budgetEur,
        @Min(1) @Max(14) Integer days,
        @Min(1) @Max(20) Integer travelers,
        Boolean freeOnly,
        List<Long> likedPlaceIds,
        @Min(1) @Max(50) Integer topK) {

    public RecommendRequest {
        interests = interests == null ? Map.of() : interests;
        days = days == null ? 3 : days;
        travelers = travelers == null ? 1 : travelers;
        freeOnly = freeOnly != null && freeOnly;
        likedPlaceIds = likedPlaceIds == null ? List.of() : likedPlaceIds;
        topK = topK == null ? 10 : topK;
    }
}
