# backend — Spring Boot 3 (Java 21)

Passerelle entre le frontend et le service Python : validation des requêtes, relais des appels,
historique des demandes (H2), gestion des erreurs, documentation OpenAPI.

```bash
# le service Python doit tourner sur http://localhost:8000 (ou définir ML_BASE_URL)
mvn spring-boot:run
mvn test
```
- Swagger UI : http://localhost:8080/swagger-ui.html
- Santé : http://localhost:8080/actuator/health
