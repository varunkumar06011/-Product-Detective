import React from 'react';

export class SafeErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("3D Component Error caught by boundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#1a1a2e',
          color: '#ff4444',
          fontSize: '11px',
          textAlign: 'center',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid #442222'
        }}>
          <div>
            <div style={{ fontSize: '24px', marginBottom: '10px' }}>⚠️</div>
            <strong>3D RENDER UNAVAILABLE</strong>
            <p style={{ opacity: 0.7, marginTop: '5px' }}>
              Your browser environment may not support WebGL or a runtime error occurred.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function isWebGLAvailable() {
  try {
    const canvas = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
  } catch (e) {
    return false;
  }
}
