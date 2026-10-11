import { apiClient } from './client.ts';
import type { ChangeRequest, StageChange, ApplyChange, ChangeProposalOut, ChangeProposalList, ChangeAppliedOut, ImpactReport, DependencyCreate, DependencyOut, DependencyList } from '../../types/core-api.ts';
import type { SessionOut, EventCreate, EventCreatedOut, EventOut, EventList, EventStatus, ConflictCheckRequest, ConflictCheckOut, TransitionRequest, ResourceList, ResourceKind, ResourceOut, ResourceInterestCreate, ResourceInterestOut, ChatMessage, ChatResponse, AgentAction, AgentActionConfirmOut, ProposalUploadOut, ProposalOut, ProposalDownloadUrlOut, ProposalStatusPatch, OverrideRequest, OverrideOut } from '../../types/core-api.ts';
export const authApi = { demoLogin: (email: string) => apiClient<SessionOut>('auth/demo-login', { method: 'POST', body: JSON.stringify({ email }) }) };
export type EventFilters = { club_id?: string; status?: EventStatus; starts_after?: string; starts_before?: string; limit?: number; offset?: number };
export const eventsApi = {
  list: (token: string, params: EventFilters = {}, signal?: AbortSignal) => apiClient<EventList>('events', { token, params, signal }),
  get: (token: string, id: string, signal?: AbortSignal) => apiClient<EventOut>(`events/${id}`, { token, signal }),
  create: (token: string, event: EventCreate, idempotencyKey: string) => apiClient<EventCreatedOut>('events', { method: 'POST', token, idempotencyKey, body: JSON.stringify(event) }),
  preview: (token: string, event: EventCreate, signal?: AbortSignal) => apiClient<ConflictCheckOut>('events/conflict-check', { method: 'POST', token, body: JSON.stringify(event), signal }),
  checkConflicts: (token: string, id: string, candidate: ConflictCheckRequest = {}, signal?: AbortSignal) => apiClient<ConflictCheckOut>(`events/${id}/conflict-check`, { method: 'POST', token, body: JSON.stringify(candidate), signal }),
  transition: (token: string, id: string, payload: TransitionRequest, idempotencyKey?: string) => apiClient<EventOut>(`events/${id}/transitions`, { method: 'POST', token, body: JSON.stringify(payload), idempotencyKey }),
};
export const resourcesApi = {
  list: (token: string, params: { kind?: ResourceKind; q?: string; limit?: number; offset?: number } = {}, signal?: AbortSignal) => apiClient<ResourceList>('resources', { token, params, signal }),
  get: (token: string, id: string) => apiClient<ResourceOut>(`resources/${id}`, { token }),
  createInterest: (token: string, payload: ResourceInterestCreate) => apiClient<ResourceInterestOut>('resources/interests', { token, method: 'POST', body: JSON.stringify(payload) }),
};
export const agentApi = {
  chat: (token: string, messages: ChatMessage[], eventId?: string | null, signal?: AbortSignal) => apiClient<ChatResponse>('agent/chat', { token, method: 'POST', body: JSON.stringify({ messages, event_id: eventId ?? null }), signal }),
  confirmAction: (token: string, id: string) => apiClient<AgentActionConfirmOut>(`agent-actions/${id}/confirm`, { token, method: 'POST' }),
  rejectAction: (token: string, id: string) => apiClient<AgentAction>(`agent-actions/${id}/reject`, { token, method: 'POST' }),
};
export const proposalsApi = {
  upload: (token: string, club: string, event: string, file: File, title: string) => {
    const body = new FormData(); body.append('file', file); body.append('title', title);
    return apiClient<ProposalUploadOut>(`clubs/${club}/events/${event}/proposals`, { token, method: 'POST', body });
  },
  get: (token: string, id: string) => apiClient<ProposalOut>(`proposals/${id}`, { token }),
  getDownloadUrl: (token: string, id: string) => apiClient<ProposalDownloadUrlOut>(`proposals/${id}/download-url`, { token }),
  review: (token: string, id: string, payload: ProposalStatusPatch) => apiClient<ProposalOut>(`proposals/${id}/status`, { token, method: 'PATCH', body: JSON.stringify(payload) }),
};
export const overridesApi = { create: (token: string, payload: OverrideRequest, idempotencyKey: string) => apiClient<OverrideOut>('overrides', { token, method: 'POST', body: JSON.stringify(payload), idempotencyKey }) };
export const changesApi = {
  preview: (token: string, id: string, payload: ChangeRequest, signal?: AbortSignal) => apiClient<ImpactReport>(`events/${id}/impact`, { token, method: 'POST', body: JSON.stringify(payload), signal }),
  stage: (token: string, id: string, payload: StageChange, idempotencyKey: string) => apiClient<ChangeProposalOut>(`events/${id}/change-proposals`, { token, method: 'POST', body: JSON.stringify(payload), idempotencyKey }),
  list: (token: string, id: string, offset = 0, signal?: AbortSignal) => apiClient<ChangeProposalList>(`events/${id}/change-proposals`, { token, params: { limit: 20, offset }, signal }),
  apply: (token: string, id: string, proposal: string, payload: ApplyChange, idempotencyKey: string) => apiClient<ChangeAppliedOut>(`events/${id}/change-proposals/${proposal}/apply`, { token, method: 'POST', body: JSON.stringify(payload), idempotencyKey }),
  dependencies: (token: string, id: string, signal?: AbortSignal) => apiClient<DependencyList>(`events/${id}/dependencies`, { token, signal }),
  register: (token: string, id: string, payload: DependencyCreate, idempotencyKey: string) => apiClient<DependencyOut>(`events/${id}/dependencies`, { token, method: 'POST', body: JSON.stringify(payload), idempotencyKey }),
};
