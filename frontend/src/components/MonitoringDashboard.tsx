import React, { useState, useEffect } from 'react';
import { 
    getMonitoringMetrics, 
    getHallucinations, 
    getErrorStats, 
    getLatencyStats,
    getMonitoringHealth 
} from '../services/api';

interface SystemMetrics {
    total_queries: number;
    failed_queries: number;
    success_rate: number;
    hallucinations_detected: number;
    hallucination_rate: number;
    latency: {
        query: LatencyStats;
        retrieval: LatencyStats;
        generation: LatencyStats;
    };
}

interface LatencyStats {
    avg_ms: number;
    min_ms: number;
    max_ms: number;
    count: number;
}

interface Hallucination {
    query_id: string;
    timestamp: string;
    query: string;
    answer: string;
    hallucination_score: number;
    source_overlap_ratio: number;
    flagged: boolean;
}

interface ErrorStats {
    total_errors: number;
    recent_errors: any[];
}

const MonitoringDashboard: React.FC = () => {
    const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
    const [hallucinations, setHallucinations] = useState<Hallucination[]>([]);
    const [errors, setErrors] = useState<ErrorStats | null>(null);
    const [health, setHealth] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'overview' | 'hallucinations' | 'errors' | 'latency'>('overview');

    const loadData = async () => {
        try {
            setLoading(true);
            const [metricsData, hallucinationsData, errorsData, healthData] = await Promise.all([
                getMonitoringMetrics(),
                getHallucinations(20),
                getErrorStats(),
                getMonitoringHealth()
            ]);
            
            setMetrics(metricsData);
            setHallucinations(hallucinationsData.hallucinations || []);
            setErrors(errorsData);
            setHealth(healthData);
            setError(null);
        } catch (err: any) {
            console.error('Failed to load monitoring data:', err);
            setError('Failed to load monitoring data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
        // Refresh every 30 seconds
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, []);

    const formatNumber = (num: number) => num.toLocaleString();
    const formatPercent = (num: number) => `${(num * 100).toFixed(1)}%`;
    const formatMs = (ms: number) => `${ms.toFixed(0)}ms`;

    const getScoreColor = (score: number) => {
        if (score < 0.3) return '#4caf50'; // Green
        if (score < 0.6) return '#ff9800'; // Orange
        return '#f44336'; // Red
    };

    if (loading && !metrics) {
        return (
            <div className="card">
                <h2>📊 Monitoring Dashboard</h2>
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                    Loading monitoring data...
                </div>
            </div>
        );
    }

    if (error && !metrics) {
        return (
            <div className="card">
                <h2>📊 Monitoring Dashboard</h2>
                <div style={{ color: 'red', padding: '20px' }}>{error}</div>
                <button onClick={loadData} className="button">Retry</button>
            </div>
        );
    }

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>📊 Monitoring Dashboard</h2>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    {health && (
                        <span style={{ 
                            fontSize: '12px', 
                            padding: '4px 8px', 
                            borderRadius: '4px',
                            backgroundColor: health.status === 'healthy' ? '#e8f5e9' : '#ffebee',
                            color: health.status === 'healthy' ? '#2e7d32' : '#c62828'
                        }}>
                            {health.status === 'healthy' ? '✓' : '✗'} {health.status}
                        </span>
                    )}
                    <button onClick={loadData} className="button" style={{ padding: '6px 12px', fontSize: '14px' }}>
                        🔄 Refresh
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '2px solid #e0e0e0' }}>
                {['overview', 'hallucinations', 'errors', 'latency'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab as any)}
                        style={{
                            padding: '10px 20px',
                            border: 'none',
                            background: 'none',
                            cursor: 'pointer',
                            borderBottom: activeTab === tab ? '3px solid #1976d2' : 'none',
                            fontWeight: activeTab === tab ? 'bold' : 'normal',
                            color: activeTab === tab ? '#1976d2' : '#666'
                        }}
                    >
                        {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    </button>
                ))}
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && metrics && (
                <div>
                    {/* Metrics Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '30px' }}>
                        <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Total Queries</div>
                            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#1976d2' }}>
                                {formatNumber(metrics.total_queries)}
                            </div>
                        </div>

                        <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Success Rate</div>
                            <div style={{ fontSize: '28px', fontWeight: 'bold', color: metrics.success_rate > 0.95 ? '#4caf50' : '#ff9800' }}>
                                {formatPercent(metrics.success_rate)}
                            </div>
                        </div>

                        <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Failed Queries</div>
                            <div style={{ fontSize: '28px', fontWeight: 'bold', color: metrics.failed_queries > 0 ? '#f44336' : '#4caf50' }}>
                                {formatNumber(metrics.failed_queries)}
                            </div>
                        </div>

                        <div style={{ padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px solid #e0e0e0' }}>
                            <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Hallucination Rate</div>
                            <div style={{ fontSize: '28px', fontWeight: 'bold', color: metrics.hallucination_rate > 0.1 ? '#f44336' : '#4caf50' }}>
                                {formatPercent(metrics.hallucination_rate)}
                            </div>
                        </div>
                    </div>

                    {/* Latency Overview */}
                    <h3>⏱️ Latency Overview</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
                        {Object.entries(metrics.latency).map(([operation, stats]) => (
                            <div key={operation} style={{ padding: '15px', backgroundColor: '#fff', border: '1px solid #e0e0e0', borderRadius: '8px' }}>
                                <div style={{ fontWeight: 'bold', marginBottom: '10px', textTransform: 'capitalize' }}>
                                    {operation}
                                </div>
                                <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
                                    Average: <strong style={{ color: '#1976d2' }}>{formatMs(stats.avg_ms)}</strong>
                                </div>
                                <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>
                                    Min: {formatMs(stats.min_ms)} | Max: {formatMs(stats.max_ms)}
                                </div>
                                <div style={{ fontSize: '12px', color: '#666' }}>
                                    Count: {formatNumber(stats.count)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Hallucinations Tab */}
            {activeTab === 'hallucinations' && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                        <h3>🚨 Hallucination Detections</h3>
                        <span style={{ fontSize: '14px', color: '#666' }}>
                            {hallucinations.length} flagged responses
                        </span>
                    </div>

                    {hallucinations.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                            ✓ No hallucinations detected - all responses are well-grounded!
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            {hallucinations.map((hal, index) => (
                                <div key={hal.query_id} style={{ 
                                    padding: '15px', 
                                    backgroundColor: '#fff', 
                                    border: `2px solid ${getScoreColor(hal.hallucination_score)}`,
                                    borderRadius: '8px'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                        <div>
                                            <span style={{ 
                                                fontSize: '12px', 
                                                padding: '4px 8px', 
                                                borderRadius: '4px',
                                                backgroundColor: getScoreColor(hal.hallucination_score),
                                                color: 'white',
                                                fontWeight: 'bold'
                                            }}>
                                                Score: {(hal.hallucination_score * 100).toFixed(0)}%
                                            </span>
                                            <span style={{ fontSize: '12px', color: '#666', marginLeft: '10px' }}>
                                                Overlap: {(hal.source_overlap_ratio * 100).toFixed(0)}%
                                            </span>
                                        </div>
                                        <span style={{ fontSize: '12px', color: '#999' }}>
                                            {new Date(hal.timestamp).toLocaleString()}
                                        </span>
                                    </div>
                                    <div style={{ marginBottom: '8px' }}>
                                        <strong style={{ fontSize: '14px', color: '#1976d2' }}>Q:</strong>
                                        <span style={{ marginLeft: '8px', fontSize: '14px' }}>{hal.query}</span>
                                    </div>
                                    <div>
                                        <strong style={{ fontSize: '14px', color: '#388e3c' }}>A:</strong>
                                        <span style={{ marginLeft: '8px', fontSize: '14px', color: '#666' }}>
                                            {hal.answer.substring(0, 200)}...
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Errors Tab */}
            {activeTab === 'errors' && errors && (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                        <h3>❌ Error Statistics</h3>
                        <span style={{ fontSize: '14px', color: '#666' }}>
                            Total: {errors.total_errors}
                        </span>
                    </div>

                    {errors.recent_errors.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                            ✓ No recent errors - system running smoothly!
                        </div>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            {errors.recent_errors.map((err, index) => (
                                <div key={index} style={{ 
                                    padding: '15px', 
                                    backgroundColor: '#fff', 
                                    border: '2px solid #f44336',
                                    borderRadius: '8px'
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                        <span style={{ 
                                            fontSize: '12px', 
                                            padding: '4px 8px', 
                                            borderRadius: '4px',
                                            backgroundColor: '#f44336',
                                            color: 'white',
                                            fontWeight: 'bold'
                                        }}>
                                            {err.error_type}
                                        </span>
                                        <span style={{ fontSize: '12px', color: '#999' }}>
                                            {new Date(err.timestamp).toLocaleString()}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>
                                        <strong>Operation:</strong> {err.operation}
                                    </div>
                                    <div style={{ fontSize: '14px', color: '#666', marginBottom: '5px' }}>
                                        <strong>Message:</strong> {err.error_message}
                                    </div>
                                    {err.retry_count > 0 && (
                                        <div style={{ fontSize: '12px', color: '#ff9800', marginTop: '5px' }}>
                                            ⚠ Retried {err.retry_count} time(s)
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Latency Tab */}
            {activeTab === 'latency' && metrics && (
                <div>
                    <h3>⏱️ Detailed Latency Statistics</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        {Object.entries(metrics.latency).map(([operation, stats]) => (
                            <div key={operation} style={{ 
                                padding: '20px', 
                                backgroundColor: '#fff', 
                                border: '1px solid #e0e0e0',
                                borderRadius: '8px'
                            }}>
                                <h4 style={{ margin: '0 0 15px 0', textTransform: 'capitalize', color: '#1976d2' }}>
                                    {operation}
                                </h4>
                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '15px' }}>
                                    <div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Average</div>
                                        <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{formatMs(stats.avg_ms)}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Count</div>
                                        <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{formatNumber(stats.count)}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Minimum</div>
                                        <div style={{ fontSize: '20px', color: '#4caf50' }}>{formatMs(stats.min_ms)}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Maximum</div>
                                        <div style={{ fontSize: '20px', color: '#f44336' }}>{formatMs(stats.max_ms)}</div>
                                    </div>
                                </div>

                                {/* Simple bar visualization */}
                                <div style={{ marginTop: '15px' }}>
                                    <div style={{ fontSize: '12px', color: '#666', marginBottom: '5px' }}>Latency Range</div>
                                    <div style={{ 
                                        height: '30px', 
                                        backgroundColor: '#e0e0e0', 
                                        borderRadius: '4px',
                                        position: 'relative',
                                        overflow: 'hidden'
                                    }}>
                                        <div style={{ 
                                            position: 'absolute',
                                            left: '0',
                                            height: '100%',
                                            width: `${(stats.avg_ms / stats.max_ms) * 100}%`,
                                            backgroundColor: '#1976d2',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: 'white',
                                            fontSize: '12px',
                                            fontWeight: 'bold'
                                        }}>
                                            Avg
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default MonitoringDashboard;
