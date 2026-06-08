// TypeScript interface for the Z-Manager bridge (supporting WebKitGTK, Tauri, and HTTP/SSE Sidecar)
import { listen } from '@tauri-apps/api/event';
import { invoke } from '@tauri-apps/api/core';

declare global {
    interface Window {
        webkit?: {
            messageHandlers: {
                zmanager: {
                    postMessage(message: string): void;
                }
            }
        };
        onPythonMessage?: (data: any) => void;
        __TAURI_INTERNALS__?: any;
    }
}

type BridgeCallback = (data: any) => void;
const callbacks = new Map<string, BridgeCallback>();

// Sidecar connection state
let sidecarPort = 8000;
let eventSource: EventSource | null = null;
let isConnecting = false;

const isTauri = typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined;

// Listen for messages from WebKitGTK (legacy/current)
if (typeof window !== 'undefined') {
    window.onPythonMessage = (data: any) => {
        console.log('[Bridge] Received from WebKitGTK:', data);
        triggerCallback(data);
    };
}

// Listen for messages from Tauri
if (isTauri) {
    console.log('[Bridge] Running under Tauri. Initializing Tauri event listener...');
    listen('sidecar-message', (event) => {
        console.log('[Bridge] Received from Tauri sidecar event:', event.payload);
        triggerCallback(event.payload);
    }).catch((err) => {
        console.error('[Bridge] Failed to listen to Tauri sidecar events:', err);
    });
}

function triggerCallback(data: any) {
    if (data) {
        if (data.requestId && callbacks.has(data.requestId)) {
            callbacks.get(data.requestId)!(data);
        } else if (data.action && callbacks.has(data.action)) {
            callbacks.get(data.action)!(data);
        }
    }
}

/**
 * Initialize HTTP/SSE connection to the Python sidecar (used in Browser mode)
 */
export function initSidecarBridge(port: number = 8000) {
    if (isTauri) {
        console.log('[Bridge] Tauri mode active, skipping SSE initialization.');
        return;
    }
    if (eventSource || isConnecting) return;
    isConnecting = true;
    sidecarPort = port;
    
    const sseUrl = `http://127.0.0.1:${port}/events`;
    console.log(`[Bridge] Connecting to Python sidecar SSE at ${sseUrl}...`);
    
    try {
        eventSource = new EventSource(sseUrl);
        
        eventSource.onopen = () => {
            console.log('[Bridge] SSE connection established successfully');
            isConnecting = false;
        };
        
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log('[Bridge] Received from SSE:', data);
                triggerCallback(data);
            } catch (e) {
                console.error('[Bridge] Error parsing SSE message:', e);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('[Bridge] SSE error, reconnecting in 2s...', error);
            eventSource?.close();
            eventSource = null;
            isConnecting = false;
            setTimeout(() => initSidecarBridge(port), 2000);
        };
    } catch (e) {
        console.error('[Bridge] Failed to create EventSource:', e);
        isConnecting = false;
    }
}

/**
 * Send a message to the Python backend and return a Promise resolving with the response
 */
export async function sendToPython(action: string, payload: any = {}): Promise<any> {
    return new Promise((resolve, reject) => {
        const requestId = Math.random().toString(36).substring(2, 9);
        const messageObj = { action, requestId, ...payload };
        
        // Register a one-time callback for this requestId
        callbacks.set(requestId, (data) => {
            callbacks.delete(requestId);
            resolve(data);
        });
        
        // Set a timeout to prevent memory leaks if the backend never responds
        const timeoutId = setTimeout(() => {
            if (callbacks.has(requestId)) {
                callbacks.delete(requestId);
                reject(new Error(`Request ${action} timed out`));
            }
        }, 15000); // 15s timeout
        
        // Wrap resolve/reject to clear timeout
        const originalCallback = callbacks.get(requestId);
        callbacks.set(requestId, (data) => {
            clearTimeout(timeoutId);
            if (originalCallback) originalCallback(data);
        });

        if (isTauri) {
            invoke('send_to_sidecar', { action, payload: messageObj })
                .catch((err) => {
                    clearTimeout(timeoutId);
                    callbacks.delete(requestId);
                    reject(err);
                });
        } else if (typeof window !== 'undefined' && window.webkit?.messageHandlers?.zmanager) {
            const messageStr = JSON.stringify(messageObj);
            window.webkit.messageHandlers.zmanager.postMessage(messageStr);
        } else {
            // Fallback to HTTP POST
            fetch(`http://127.0.0.1:${sidecarPort}/api/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })
            .then((res) => res.json())
            .then((data) => {
                clearTimeout(timeoutId);
                callbacks.delete(requestId);
                resolve(data);
            })
            .catch((err) => {
                clearTimeout(timeoutId);
                callbacks.delete(requestId);
                reject(err);
            });
        }
    });
}

/**
 * Register a callback for a specific action from Python
 */
export function onPython(action: string, callback: BridgeCallback) {
    callbacks.set(action, callback);
}
export { sidecarPort };
