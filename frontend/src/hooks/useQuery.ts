import { useState } from 'react';
import { fetchQueryResults } from '../services/api';

export const useQuery = () => {
    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const executeQuery = async (query: string) => {
        if (!query) {
            setError('Query cannot be empty');
            return;
        }

        setLoading(true);
        setError(null);
        try {
            const data = await fetchQueryResults(query);
            setResults(data);
        } catch (err: any) {
            setError(err?.message || 'Failed to fetch results');
        } finally {
            setLoading(false);
        }
    };

    return { results, loading, error, executeQuery };
};

export default useQuery;