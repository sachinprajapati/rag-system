import { useState } from 'react';
import { uploadDocument } from '../services/api';

interface Document {
    id: string;
    filename: string;
    [key: string]: any;
}

export const useDocuments = () => {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const addDocument = async (file: File) => {
        setLoading(true);
        setError(null);
        try {
            const response = await uploadDocument(file);
            setDocuments((prevDocs) => [...prevDocs, response.data]);
        } catch (err: any) {
            setError(err?.message || 'Failed to upload document');
        } finally {
            setLoading(false);
        }
    };

    return {
        documents,
        loading,
        error,
        addDocument,
    };
};

export default useDocuments;