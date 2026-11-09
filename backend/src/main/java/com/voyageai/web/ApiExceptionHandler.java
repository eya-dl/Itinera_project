package com.voyageai.web;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;

import java.util.LinkedHashMap;
import java.util.Map;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> validation(MethodArgumentNotValidException e) {
        Map<String, String> fields = new LinkedHashMap<>();
        e.getBindingResult().getFieldErrors()
                .forEach(f -> fields.put(f.getField(), f.getDefaultMessage()));
        return ResponseEntity.badRequest().body(Map.of("error", "validation", "fields", fields));
    }

    /** Erreur 4xx du service Python (ville inconnue, lieu introuvable...) : on relaie le statut. */
    @ExceptionHandler(HttpClientErrorException.class)
    public ResponseEntity<Map<String, Object>> mlClientError(HttpClientErrorException e) {
        return ResponseEntity.status(e.getStatusCode())
                .body(Map.of("error", "ml_service", "detail", e.getResponseBodyAsString()));
    }

    @ExceptionHandler(HttpServerErrorException.class)
    public ResponseEntity<Map<String, Object>> mlServerError(HttpServerErrorException e) {
        return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                .body(Map.of("error", "ml_service_failure", "detail", "Le service de recommandation a échoué."));
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<Map<String, Object>> mlUnavailable(ResourceAccessException e) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                .body(Map.of("error", "ml_service_unavailable", "detail", "Le service de recommandation est injoignable."));
    }
}
