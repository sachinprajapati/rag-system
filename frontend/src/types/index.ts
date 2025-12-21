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
}

export interface ProcessingStatus {
    isProcessing: boolean;
    message: string;
}