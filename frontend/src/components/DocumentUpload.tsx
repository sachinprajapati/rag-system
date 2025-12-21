import React, { useState } from 'react';
import { uploadDocument } from '../services/api';

const DocumentUpload: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [message, setMessage] = useState('');

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        if (event.target.files && event.target.files.length > 0) {
            setFile(event.target.files[0]);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setMessage('Please select a file to upload.');
            return;
        }

        setUploading(true);
        setMessage('');

        try {
            const response = await uploadDocument(file);
            const chunks = response.chunks_processed || 0;
            setMessage(`File uploaded successfully! Processed ${chunks} chunks.`);
            setFile(null);
        } catch (error: any) {
            console.error('Upload error:', error);
            const errorMsg = error.response?.data?.detail || error.message || 'Error uploading file. Please try again.';
            setMessage(errorMsg);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div>
            <h2>Upload Document</h2>
            <input type="file" onChange={handleFileChange} />
            <button onClick={handleUpload} disabled={uploading}>
                {uploading ? 'Uploading...' : 'Upload'}
            </button>
            {message && <p>{message}</p>}
        </div>
    );
};

export default DocumentUpload;