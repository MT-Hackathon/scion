// BLUEPRINT: base-api-service
// STRUCTURAL: @Injectable class, inject(HttpClient), protected typed HTTP methods, baseUrl composition
// ILLUSTRATIVE: apiConfig import path, BaseApiService name, environment token (replace with your config strategy)

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { apiConfig } from '@env/environment'; // ILLUSTRATIVE: update to your environment/config token

@Injectable({ providedIn: 'root' })
export class BaseApiService { // ILLUSTRATIVE: rename to match your module (e.g., CoreApiService)
  protected readonly http = inject(HttpClient);
  protected readonly baseUrl = apiConfig.baseUrl; // ILLUSTRATIVE: or inject as InjectionToken

  protected get<T>(endpoint: string, params?: HttpParams): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}${endpoint}`, { params });
  }

  protected post<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.post<T>(`${this.baseUrl}${endpoint}`, body);
  }

  protected put<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.put<T>(`${this.baseUrl}${endpoint}`, body);
  }

  protected patch<T>(endpoint: string, body: unknown): Observable<T> {
    return this.http.patch<T>(`${this.baseUrl}${endpoint}`, body);
  }

  protected delete<T>(endpoint: string): Observable<T> {
    return this.http.delete<T>(`${this.baseUrl}${endpoint}`);
  }
}

// --- Domain service extension pattern ---
// ILLUSTRATIVE: Replace EntityService, Entity, and '/entities' with your domain names.
//
// @Injectable({ providedIn: 'root' })
// export class EntityService extends BaseApiService {
//   getAll(): Observable<Entity[]> {
//     return this.get<Entity[]>('/entities');
//   }
//
//   getById(id: string): Observable<Entity> {
//     return this.get<Entity>(`/entities/${id}`);
//   }
//
//   create(body: Partial<Entity>): Observable<Entity> {
//     return this.post<Entity>('/entities', body);
//   }
//
//   update(id: string, body: Partial<Entity>): Observable<Entity> {
//     return this.put<Entity>(`/entities/${id}`, body);
//   }
// }
