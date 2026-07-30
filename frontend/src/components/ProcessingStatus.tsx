import React from 'react';

const ProcessingStatus: React.FC<{ isProcessing: boolean }> = ({ isProcessing }) => (
    isProcessing ? <div className="processing-status">Preparing your answer…</div> : null
);

export default ProcessingStatus;
