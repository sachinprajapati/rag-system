import React from 'react';

interface ResultDisplayProps {
    results: Array<{
        title: string;
        content: string;
    }>;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({ results }) => {
    return (
        <div>
            <h2>Query Results</h2>
            {results.length === 0 ? (
                <p>No results found.</p>
            ) : (
                <ul>
                    {results.map((result, index) => (
                        <li key={index}>
                            <h3>{result.title}</h3>
                            <p>{result.content}</p>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default ResultDisplay;