package com.voyageai.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;

import java.util.List;
import java.util.Map;

/** Demande d'itinéraire : la ville est obligatoire. */
public record ItineraryRequest(
        @NotBlank String city,
        Map<@Pattern(regexp = "sea|culture|nature|amusement|shopping|religious") String,
                @Min(0) @Max(5) Integer> interests,
        @Positive Double budgetEur,
        @Min(1) @Max(14) Integer days,
        @Min(1) @Max(20) Integer travelers,
        Boolean freeOnly,
        List<Long> likedPlaceIds,
        @Min(120) @Max(720) Integer dailyMinutes,
        @Min(6) @Max(12) Integer startHour) {

    public ItineraryRequest {
        interests = interests == null ? Map.of() : interests;
        days = days == null ? 3 : days;
        travelers = travelers == null ? 1 : travelers;
        freeOnly = freeOnly != null && freeOnly;
        likedPlaceIds = likedPlaceIds == null ? List.of() : likedPlaceIds;
        dailyMinutes = dailyMinutes == null ? 480 : dailyMinutes;
        startHour = startHour == null ? 9 : startHour;
    }
}
