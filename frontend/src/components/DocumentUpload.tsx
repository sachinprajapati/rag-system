import React, { useEffect, useRef, useState } from 'react';
import { deleteDocument, listDocuments, reindexDocument, uploadDocument } from '../services/api';

interface ManagedDocument {
    file_name: string;
    chunk_count: number;
    file_size_bytes?: number;
    file_type?: string;
    page_count?: number;
    uploaded_at?: string;
    can_reindex?: boolean;
}

const fileSize = (bytes?: number) => {
    if (bytes === undefined || bytes === null) return 'Size unavailable';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const documentType = (document: ManagedDocument) => document.file_type || document.file_name.split('.').pop()?.toUpperCase() || 'FILE';

const DocumentUpload: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');
    const [documents, setDocuments] = useState<ManagedDocument[]>([]);
    const [loadingDocuments, setLoadingDocuments] = useState(true);
    const [workingFile, setWorkingFile] = useState<string | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const loadDocuments = async () => {
        try { setLoadingDocuments(true); const response = await listDocuments(); setDocuments(response.documents || []); }
        catch { setMessage('Could not load the document library.'); }
        finally { setLoadingDocuments(false); }
    };
    useEffect(() => { loadDocuments(); }, []);

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true); setMessage('');
        try {
            const response = await uploadDocument(file);
            setMessage(`${file.name} indexed · ${response.chunks_processed || 0} chunks ready for answers.`);
            setFile(null); if (inputRef.current) inputRef.current.value = '';
            await loadDocuments();
        } catch (error: any) { setMessage(error.response?.data?.detail || 'Upload failed. Please try again.'); }
        finally { setUploading(false); }
    };
    const handleDelete = async (document: ManagedDocument) => {
        if (!confirm(`Delete ${document.file_name} from the knowledge base?`)) return;
        setWorkingFile(document.file_name); setMessage('');
        try { await deleteDocument(document.file_name); setMessage(`${document.file_name} was removed.`); await loadDocuments(); }
        catch (error: any) { setMessage(error.response?.data?.detail || 'Could not delete this document.'); }
        finally { setWorkingFile(null); }
    };
    const handleReindex = async (document: ManagedDocument) => {
        setWorkingFile(document.file_name); setMessage('');
        try { const response = await reindexDocument(document.file_name); setMessage(`${document.file_name} re-indexed · ${response.chunks_processed || 0} chunks refreshed.`); await loadDocuments(); }
        catch (error: any) { setMessage(error.response?.data?.detail || 'Could not re-index this document.'); }
        finally { setWorkingFile(null); }
    };

    return <section className="knowledge-base">
        <div className="document-bar">
            <div className="document-bar-icon">⌁</div>
            <div className="document-bar-copy"><strong>Knowledge base</strong><span>{file ? `${file.name} · ${fileSize(file.size)} ready to index` : `${documents.length} ${documents.length === 1 ? 'document' : 'documents'} available to ground answers`}</span></div>
            <input ref={inputRef} id="document-file" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <label className="upload-picker" htmlFor="document-file">{file ? 'Change file' : 'Upload file'}</label>
            {file && <button className="upload-action" onClick={handleUpload} disabled={uploading}>{uploading ? 'Indexing…' : 'Add to knowledge base'}</button>}
        </div>
        {message && <div className={`upload-feedback ${message.includes('failed') || message.includes('Could not') ? 'error' : ''}`}>{message}</div>}
        <div className="document-manager">
            <div className="document-manager-heading"><div><span className="eyebrow">DOCUMENT LIBRARY</span><h2>Your indexed sources</h2></div><button className="document-refresh" onClick={loadDocuments} disabled={loadingDocuments} title="Refresh document list">↻ Refresh</button></div>
            {loadingDocuments ? <div className="document-manager-state">Loading your documents…</div> : !documents.length ? <div className="document-manager-empty"><div>▱</div><strong>No documents indexed yet</strong><span>Upload a file above and it will appear here when indexing completes.</span></div> : <div className="document-list">
                {documents.map((document) => <article className="document-item" key={document.file_name}>
                    <div className="document-file-icon">{documentType(document).slice(0, 3)}</div>
                    <div className="document-details"><strong title={document.file_name}>{document.file_name}</strong><div className="document-metadata"><span className="document-status"><i />Indexed</span><span>{fileSize(document.file_size_bytes)}</span>{document.page_count ? <span>{document.page_count} {document.page_count === 1 ? 'page' : 'pages'}</span> : null}<span>{document.chunk_count} {document.chunk_count === 1 ? 'chunk' : 'chunks'}</span>{document.uploaded_at ? <span>Updated {new Date(document.uploaded_at).toLocaleDateString()}</span> : null}</div></div>
                    <div className="document-actions"><button onClick={() => handleReindex(document)} disabled={workingFile !== null || !document.can_reindex} title={document.can_reindex ? 'Re-index this document' : 'Re-upload this legacy document to index it again'}>{workingFile === document.file_name ? 'Working…' : '↻ Re-index'}</button><button className="document-delete" onClick={() => handleDelete(document)} disabled={workingFile !== null} title="Delete document">Delete</button></div>
                </article>)}
            </div>}
        </div>
    </section>;
};
export default DocumentUpload;
