import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getConversation, queryRAGSystem, uploadDocument } from '../services/api';

interface ResultTable {
    title: string;
    columns: string[];
    rows: string[][];
}

interface QueryResult {
    query: string;
    answer: string;
    retrieved_documents: RetrievedDocument[];
    sources: string[];
    conversation_id?: string;
    table?: ResultTable;
}

interface RetrievedDocument {
    text: string;
    file_name: string;
    score?: number;
    rank?: number;
    search_method?: string;
    chunk_index?: number;
    page_number?: number;
    row_number?: number;
    chunk_role?: string;
}

interface Message {
    message_id: string;
    query: string;
    answer: string;
    sources: string[];
    timestamp: string;
    metadata?: { table?: ResultTable; citation_documents?: RetrievedDocument[] };
}

type SearchMethod = 'vector' | 'keyword' | 'hybrid';

interface QueryInterfaceProps {
    activeConversationId: string | null;
    onConversationCreated?: (conversationId: string) => void;
}

const QueryInterface: React.FC<QueryInterfaceProps> = ({ activeConversationId, onConversationCreated }) => {
    const acceptedAttachmentExtensions = ['pdf', 'csv', 'docx'];
    const [query, setQuery] = useState('');
    const [result, setResult] = useState<QueryResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [searchMethod, setSearchMethod] = useState<SearchMethod>('hybrid');
    const [topK, setTopK] = useState(5);
    const [history, setHistory] = useState<Message[]>([]);
    const [conversationTitle, setConversationTitle] = useState('');
    // Keep a just-submitted prompt in the stream while the API is working.
    // The server history replaces it once the response has been persisted.
    const [pendingQuery, setPendingQuery] = useState<string | null>(null);
    const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
    const [citationDocuments, setCitationDocuments] = useState<RetrievedDocument[] | null>(null);
    const [activeCitationIndex, setActiveCitationIndex] = useState(0);
    const [isDraggingAttachment, setIsDraggingAttachment] = useState(false);
    const [attachmentStatus, setAttachmentStatus] = useState<string | null>(null);
    const [attachmentError, setAttachmentError] = useState<string | null>(null);
    const [uploadingAttachment, setUploadingAttachment] = useState(false);
    const attachmentInputRef = useRef<HTMLInputElement>(null);

    const uploadAttachment = async (file?: File) => {
        if (!file || uploadingAttachment) return;
        const extension = file.name.split('.').pop()?.toLowerCase();
        if (!extension || !acceptedAttachmentExtensions.includes(extension)) {
            setAttachmentStatus(null);
            setAttachmentError('Attach a PDF, CSV, or DOCX file.');
            return;
        }

        setUploadingAttachment(true);
        setAttachmentError(null);
        setAttachmentStatus(`Indexing ${file.name}…`);
        try {
            const response = await uploadDocument(file);
            setAttachmentStatus(`${file.name} indexed · ${response.chunks_processed || 0} chunks ready.`);
        } catch (err: any) {
            setAttachmentStatus(null);
            setAttachmentError(err?.response?.data?.detail || 'Could not index this attachment. Please try again.');
        } finally {
            setUploadingAttachment(false);
            if (attachmentInputRef.current) attachmentInputRef.current.value = '';
        }
    };

    const copyMessage = async (messageId: string, text: string) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedMessageId(messageId);
            window.setTimeout(() => {
                setCopiedMessageId((currentId) => currentId === messageId ? null : currentId);
            }, 1800);
        } catch (err) {
            console.error('Unable to copy message:', err);
        }
    };

    const renderCopyButton = (messageId: string, text: string) => (
        <button
            className="copy-message-button"
            type="button"
            onClick={() => copyMessage(messageId, text)}
            aria-label={copiedMessageId === messageId ? 'Message copied' : 'Copy message'}
            title={copiedMessageId === messageId ? 'Copied' : 'Copy message'}
        >
            {copiedMessageId === messageId ? 'Copied' : 'Copy'}
        </button>
    );

    const renderTable = (table?: ResultTable) => table && (
        <section className="result-table" aria-label={table.title}>
            <div className="result-table-title">{table.title}</div>
            <div className="result-table-scroll">
                <table>
                    <thead><tr>{table.columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead>
                    <tbody>{table.rows.map((row, rowIndex) => <tr key={`${row.join('-')}-${rowIndex}`}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>)}</tbody>
                </table>
            </div>
        </section>
    );

    const renderMarkdown = (content: string) => (
        <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
    );

    const openCitationPreview = (documents: RetrievedDocument[], preferredIndex = 0) => {
        if (!documents.length) return;
        setCitationDocuments(documents);
        setActiveCitationIndex(preferredIndex);
    };

    const citationLocation = (document: RetrievedDocument) => {
        const location = [];
        if (document.page_number) location.push(`Page ${document.page_number}`);
        if (document.row_number) location.push(`Row ${document.row_number}`);
        if (document.chunk_index !== undefined) location.push(`Chunk ${document.chunk_index + 1}`);
        return location.length ? location.join(' · ') : 'Retrieved passage';
    };

    const relevanceLabel = (document: RetrievedDocument, index: number) => {
        if (document.search_method === 'exact_structured_record') return 'Exact record';
        const rank = document.rank || index + 1;
        if (rank === 1) return 'Top match';
        if (rank <= 3) return 'Strong match';
        return 'Related source';
    };

    const renderSourcePills = (sources: string[], documents?: RetrievedDocument[]) => (
        <div className="source-pills" aria-label="Citations">
            {documents?.length ? documents.map((document, index) => (
                    <button key={`${document.file_name}-${document.chunk_index}-${index}`} type="button" onClick={() => openCitationPreview([document])} title={`Open ${citationLocation(document)} from ${document.file_name}`}>
                        ⌁ {document.file_name} · {citationLocation(document)}
                    </button>
                )) : sources.map((source, index) => <span key={`${source}-${index}`}>⌁ {source}</span>)}
        </div>
    );

    const formatMessageTimestamp = (timestamp?: string) => {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) return '';

        return new Intl.DateTimeFormat(undefined, {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
        }).format(date);
    };

    useEffect(() => {
        const loadConversation = async () => {
            if (!activeConversationId) {
                setHistory([]);
                setConversationTitle('');
                setResult(null);
                setPendingQuery(null);
                return;
            }
            try {
                const conversation = await getConversation(activeConversationId);
                setHistory(conversation.messages || []);
                setConversationTitle(conversation.title || 'Untitled chat');
                setResult(null);
            } catch (err) {
                console.error('Failed to load conversation:', err);
                setHistory([]);
                setConversationTitle('');
            }
        };
        loadConversation();
    }, [activeConversationId]);

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!query.trim() || loading) return;
        const submittedQuery = query.trim();
        setQuery('');
        setPendingQuery(submittedQuery);
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await queryRAGSystem(submittedQuery, topK, searchMethod, activeConversationId || undefined);
            setResult(data);
            const conversationId = data.conversation_id || activeConversationId;
            if (data.conversation_id && !activeConversationId) onConversationCreated?.(data.conversation_id);
            if (conversationId) {
                const conversation = await getConversation(conversationId);
                setHistory(conversation.messages || []);
                setConversationTitle(conversation.title || 'Untitled chat');
            }
            setPendingQuery(null);
        } catch (err: any) {
            console.error('Query error:', err);
            setError(err?.response?.data?.detail || err.message || 'Unable to generate an answer right now.');
        } finally {
            setLoading(false);
        }
    };

    const renderMessage = (message: Message, hideAnswer = false) => (
        <div className="message-exchange" key={message.message_id}>
            <article className="chat-message user-message"><div className="message-avatar">You</div><div className="message-body"><p>{message.query}</p>{renderCopyButton(`${message.message_id}-query`, message.query)}</div></article>
            {!hideAnswer && <article className="chat-message assistant-message"><div className="message-avatar assistant-avatar">AI</div><div className="message-body"><div className="message-label">Askwise</div>{renderMarkdown(message.answer)}{renderCopyButton(`${message.message_id}-answer`, message.answer)}{renderTable(message.metadata?.table)}{message.sources?.length > 0 && renderSourcePills(message.sources, message.metadata?.citation_documents)}</div></article>}
            {formatMessageTimestamp(message.timestamp) && <time className="message-timestamp" dateTime={message.timestamp}>{formatMessageTimestamp(message.timestamp)}</time>}
        </div>
    );

    // A completed query is saved to the conversation before its API response is
    // returned. Keep the saved user message, but let the latest-result block
    // render the matching answer so it is shown only once with its evidence.
    const latestHistoryMessageIndex = result
        ? history.findLastIndex((message) => message.query === result.query && message.answer === result.answer)
        : -1;

    const hasMessages = history.length > 0 || Boolean(result) || Boolean(pendingQuery);

    return (
        <section className="chat-shell">
            <div className="chat-heading">
                <div>
                    <span className="eyebrow">DOCUMENT INTELLIGENCE</span>
                    <h2>{conversationTitle || 'How can I help you today?'}</h2>
                    <p>{conversationTitle ? 'Continue asking questions about your knowledge base.' : 'Ask anything from your uploaded documents.'}</p>
                </div>
                {activeConversationId && <span className="active-chat-badge">● Active chat</span>}
            </div>

            <div className={`message-stream ${!hasMessages ? 'empty-stream' : ''}`}>
                {!hasMessages && <div className="welcome-state"><div className="welcome-orb">✦</div><h3>Ready when you are</h3><p>Upload a document, then ask a focused question to find the answers that matter.</p><div className="prompt-suggestions"><button onClick={() => setQuery('Summarize the key points in my documents')}>Summarize key points</button><button onClick={() => setQuery('What are the most important action items?')}>Find action items</button><button onClick={() => setQuery('What should I know first?')}>What should I know first?</button></div></div>}
                {history.map((message, index) => renderMessage(message, index === latestHistoryMessageIndex))}
                {pendingQuery && <article className="chat-message user-message pending-message"><div className="message-avatar">You</div><div className="message-body"><p>{pendingQuery}</p>{renderCopyButton('pending-query', pendingQuery)}</div></article>}
                {result && <div className="message-exchange"><article className="chat-message assistant-message latest-answer"><div className="message-avatar assistant-avatar">AI</div><div className="message-body"><div className="message-label">Askwise <span>{result.retrieved_documents?.[0]?.search_method || searchMethod} search</span></div>{renderMarkdown(result.answer)}{renderCopyButton('latest-answer', result.answer)}{renderTable(result.table)}{result.sources?.length > 0 && renderSourcePills(result.sources, result.retrieved_documents)}{result.retrieved_documents?.length > 0 && <details className="evidence"><summary>View {result.retrieved_documents.length} retrieved sources</summary>{result.retrieved_documents.map((doc, index) => <button className="evidence-item" type="button" onClick={() => openCitationPreview(result.retrieved_documents, index)} key={`${doc.file_name}-${index}`}><strong>{doc.file_name}</strong><span>{relevanceLabel(doc, index)}</span><small>{citationLocation(doc)}</small><p>{doc.text}</p></button>)}</details>}</div></article>{latestHistoryMessageIndex >= 0 && formatMessageTimestamp(history[latestHistoryMessageIndex].timestamp) && <time className="message-timestamp" dateTime={history[latestHistoryMessageIndex].timestamp}>{formatMessageTimestamp(history[latestHistoryMessageIndex].timestamp)}</time>}</div>}
                {loading && <article className="chat-message assistant-message"><div className="message-avatar assistant-avatar">AI</div><div className="typing-indicator"><i></i><i></i><i></i></div></article>}
            </div>

            {error && <div className="query-error">{error}</div>}
            <form className="composer" onSubmit={handleSubmit}>
                <input ref={attachmentInputRef} className="composer-attachment-input" type="file" accept=".pdf,.csv,.docx,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => uploadAttachment(event.target.files?.[0])} />
                <div
                    className={`composer-dropzone ${isDraggingAttachment ? 'is-dragging' : ''} ${uploadingAttachment ? 'is-uploading' : ''}`}
                    role="button"
                    tabIndex={0}
                    aria-label="Attach a PDF, CSV, or DOCX document"
                    onClick={() => !uploadingAttachment && attachmentInputRef.current?.click()}
                    onKeyDown={(event) => { if ((event.key === 'Enter' || event.key === ' ') && !uploadingAttachment) { event.preventDefault(); attachmentInputRef.current?.click(); } }}
                    onDragEnter={(event) => { event.preventDefault(); setIsDraggingAttachment(true); }}
                    onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; setIsDraggingAttachment(true); }}
                    onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setIsDraggingAttachment(false); }}
                    onDrop={(event) => { event.preventDefault(); setIsDraggingAttachment(false); uploadAttachment(event.dataTransfer.files?.[0]); }}
                >
                    <span className="composer-dropzone-icon" aria-hidden="true">⌁</span>
                    <span><strong>{uploadingAttachment ? 'Indexing attachment…' : 'Drop a document here'}</strong><small>PDF, CSV, or DOCX · or click to browse</small></span>
                </div>
                {(attachmentStatus || attachmentError) && <div className={`composer-attachment-status ${attachmentError ? 'error' : ''}`} role="status">{attachmentError || attachmentStatus}</div>}
                <textarea value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSubmit(event); } }} placeholder="Message your documents…" rows={1} />
                <div className="composer-footer">
                    <details className="composer-advanced">
                        <summary>Advanced <span aria-hidden="true">⌄</span></summary>
                        <div className="composer-controls">
                            <label>Search method
                                <select value={searchMethod} onChange={(event) => setSearchMethod(event.target.value as SearchMethod)} aria-label="Search method"><option value="hybrid">Hybrid search</option><option value="vector">Semantic search</option><option value="keyword">Keyword search</option></select>
                            </label>
                            <label>Sources <input type="number" min="1" max="20" value={topK} onChange={(event) => setTopK(Number(event.target.value) || 5)} /></label>
                        </div>
                    </details>
                    <button className="send-button" type="submit" disabled={!query.trim() || loading} aria-label="Send message">↑</button>
                </div>
            </form>
            <p className="composer-disclaimer">Askwise can make mistakes. Verify important information against the source documents.</p>
            {citationDocuments && citationDocuments[activeCitationIndex] && <div className="citation-backdrop" role="presentation" onMouseDown={() => setCitationDocuments(null)}><section className="citation-preview" role="dialog" aria-modal="true" aria-labelledby="citation-preview-title" onMouseDown={(event) => event.stopPropagation()}><div className="citation-preview-heading"><div><span className="eyebrow">SOURCE PREVIEW</span><h3 id="citation-preview-title">{citationDocuments[activeCitationIndex].file_name}</h3><p>{citationLocation(citationDocuments[activeCitationIndex])}</p></div><button type="button" className="citation-close" onClick={() => setCitationDocuments(null)} aria-label="Close source preview">×</button></div>{citationDocuments.length > 1 && <div className="citation-choices" aria-label="Retrieved passages">{citationDocuments.map((document, index) => <button type="button" className={index === activeCitationIndex ? 'active' : ''} onClick={() => setActiveCitationIndex(index)} key={`${document.file_name}-${document.chunk_index}-${index}`}>{citationLocation(document)}</button>)}</div>}<div className="citation-preview-text">{citationDocuments[activeCitationIndex].text}</div><p className="citation-relevance">{relevanceLabel(citationDocuments[activeCitationIndex], activeCitationIndex)} for this question</p></section></div>}
        </section>
    );
};

export default QueryInterface;
