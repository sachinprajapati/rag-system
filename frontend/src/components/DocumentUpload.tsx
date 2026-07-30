import React, { useRef, useState } from 'react';
import { uploadDocument } from '../services/api';

const DocumentUpload: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setMessage('');
        try {
            const response = await uploadDocument(file);
            setMessage(`${file.name} is ready · ${response.chunks_processed || 0} chunks indexed`);
            setFile(null);
            if (inputRef.current) inputRef.current.value = '';
        } catch (error: any) {
            setMessage(error.response?.data?.detail || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <section className="document-bar">
            <div className="document-bar-icon">⌁</div>
            <div className="document-bar-copy"><strong>Knowledge base</strong><span>{file ? file.name : 'Add documents to ground your answers'}</span></div>
            <input ref={inputRef} id="document-file" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
            <label className="upload-picker" htmlFor="document-file">{file ? 'Change file' : 'Upload file'}</label>
            {file && <button className="upload-action" onClick={handleUpload} disabled={uploading}>{uploading ? 'Indexing…' : 'Add to knowledge base'}</button>}
            {message && <span className="upload-message">{message}</span>}
        </section>
    );
};

export default DocumentUpload;
