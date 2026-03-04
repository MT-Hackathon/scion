// BLUEPRINT: Global exception handler mapping domain exceptions to RFC 7807-aligned responses
// STRUCTURAL: @RestControllerAdvice class, structured logger, @ExceptionHandler methods,
//             catch-all fallback, ErrorResponse record with Instant timestamp
// ILLUSTRATIVE: ResourceNotFoundException binding, field names, log messages

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.Instant;
import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /**
     * Handles guard clause violations where a required entity does not exist.
     * For expected "not found" business outcomes, use typed result records instead.
     */
    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        ErrorResponse error = new ErrorResponse("NOT_FOUND", ex.getMessage(), Instant.now());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
    }

    /**
     * Handles @Valid constraint violations on request bodies.
     * Joins all field errors into a single human-readable message.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .collect(Collectors.joining(", "));
        log.warn("Validation failed: {}", message);
        ErrorResponse error = new ErrorResponse("VALIDATION_ERROR", message, Instant.now());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(error);
    }

    /**
     * Catch-all for unhandled exceptions. Logs full stack trace; returns generic 500.
     * Never expose internal details in the message field.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex) {
        log.error("Unhandled exception", ex);
        ErrorResponse error = new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred", Instant.now());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}

/**
 * Standard error response structure. Code is a machine-readable enum string.
 * Instant ensures timezone-unambiguous timestamps in API responses.
 * Never include stack traces or internal details in the message field.
 */
record ErrorResponse(String code, String message, Instant timestamp) {}
