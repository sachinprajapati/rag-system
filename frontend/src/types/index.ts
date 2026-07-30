export interface Document {
    id: string;
    title: string;
    content: string;
    createdAt: Date;
}

export type SearchMethod = 'vector' | 'keyword' | 'hybrid';

export interface Query {
    id: string;
    queryText: string;
    createdAt: Date;
    searchMethod?: SearchMethod;
}

export interface QueryResult {
    documentId: string;
    score: number;
    searchMethod?: SearchMethod;
}

export interface RetrievedDocument {
    text: string;
    file_name: string;
    score: number;
    rank?: number;
    search_method?: string;
    chunk_index?: number;
    tenant_id?: string;
}

export interface RAGQueryResponse {
    query: string;
    answer: string;
    retrieved_documents: RetrievedDocument[];
    sources: string[];
    tenant_id?: string;
    conversation_id?: string;
}

export interface Message {
    message_id: string;
    conversation_id: string;
    query: string;
    answer: string;
    sources: string[];
    timestamp: string;
    metadata?: Record<string, any>;
}

export interface Conversation {
    conversation_id: string;
    tenant_id: string;
    user_id: string;
    title: string;
    messages: Message[];
    created_at: string;
    updated_at: string;
    metadata?: Record<string, any>;
}

export interface ConversationSummary {
    conversation_id: string;
    title: string;
    message_count: number;
    created_at: string;
    updated_at: string;
    last_query?: string;
}

export interface ProcessingStatus {
    isProcessing: boolean;
    message: string;
}