import React from 'react';

const ProcessingStatus: React.FC<{ isProcessing: boolean }> = ({ isProcessing }) => {
    return (
        <div>
            {isProcessing ? (
                <p>Processing your request, please wait...</p>
            ) : (
                <p>Your request has been processed.</p>
            )}
        </div>
    );
};

export default ProcessingStatus;