package com.example.javis2.controller;

import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;
import java.util.Map;

@RestController
@RequestMapping("/api/chat")
@CrossOrigin(origins = "http://localhost:3000") // 리액트 포트에서 오는 요청 허용
public class ChatController {

    private final WebClient webClient;

    public ChatController(WebClient.Builder webClientBuilder) {
        this.webClient = webClientBuilder.baseUrl("http://localhost:5000").build();
    }

    @PostMapping("/ask")
    public Map askAi(@RequestBody Map<String, Object> request) {
        System.out.println("사용자 질문: " + request.get("message") + " / 회사ID: " + request.get("company_id"));

        return webClient.post()
                .uri("/api/ai/chat")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(Map.class)
                .block();
    }

    @PostMapping("/upload")
    public Mono<Map> uploadFile(
            @RequestPart("file") MultipartFile file,
            @RequestPart("company_id") String companyId) { // FormData 특성상 String으로 받지만 내부적으로 처리됨

        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", file.getResource());
        builder.part("company_id", companyId);

        return webClient.post()
                .uri("/api/ai/upload")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .bodyValue(builder.build())
                .retrieve()
                .bodyToMono(Map.class)
                .doOnNext(res -> System.out.println("파일 업로드 브릿지 성공: " + res));

    }
}