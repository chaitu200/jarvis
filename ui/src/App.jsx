import { useState, useEffect, useRef } from 'react';

function App() {
  const [state, setState] = useState('idle'); // hidden, idle, listening, speaking, processing
  const [statusText, setStatusText] = useState('BOOTING...');
  const [subtitle, setSubtitle] = useState('');
  
  const [audioLevels, setAudioLevels] = useState(Array(12).fill(0.1));
  
  const wsRef = useRef(null);
  const hideTimeoutRef = useRef(null);
  const hideDelayRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const microphoneRef = useRef(null);
  const rafIdRef = useRef(null);

  const startStandbyTimer = () => {
    if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    if (hideDelayRef.current) clearTimeout(hideDelayRef.current);
    
    hideTimeoutRef.current = setTimeout(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'standby' }));
      }
    }, 25000); // 25 seconds of silence
  };

  const clearStandbyTimer = () => {
    if (hideTimeoutRef.current) clearTimeout(hideTimeoutRef.current);
    if (hideDelayRef.current) clearTimeout(hideDelayRef.current);
  };

  // Setup Web Audio for real-time visualizer
  const initAudioVisualizer = async () => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
        analyserRef.current = audioContextRef.current.createAnalyser();
        analyserRef.current.fftSize = 64; // Gives us 32 bins
        analyserRef.current.smoothingTimeConstant = 0.8;
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        microphoneRef.current = audioContextRef.current.createMediaStreamSource(stream);
        microphoneRef.current.connect(analyserRef.current);
      }
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }
      updateVisualizer();
    } catch (err) {
      console.error("Microphone access denied or error:", err);
    }
  };

  const stopAudioVisualizer = () => {
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }
    setAudioLevels(Array(12).fill(0.1));
  };

  const updateVisualizer = () => {
    if (analyserRef.current) {
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      analyserRef.current.getByteFrequencyData(dataArray);
      
      // Sample 12 bins for a smoother circular or wide look
      const levels = [];
      for (let i = 0; i < 12; i++) {
        // Skip lowest frequencies (0, 1) to avoid constant hum
        levels.push(Math.max(0.1, (dataArray[i + 2] / 255) || 0.1));
      }
      setAudioLevels(levels);
    }
    rafIdRef.current = requestAnimationFrame(updateVisualizer);
  };

  useEffect(() => {
    if (state === 'listening') {
      initAudioVisualizer();
      startStandbyTimer();
    } else if (state === 'processing' || state === 'speaking') {
      clearStandbyTimer();
    } else if (state === 'idle') {
      startStandbyTimer();
    } else if (state === 'hidden') {
      clearStandbyTimer();
    }
    
    if (state !== 'speaking' && state !== 'listening') {
      stopAudioVisualizer();
    }
    
    // Manage visibility via IPC
    if (window.ipcRenderer) {
      if (state === 'hidden') {
        window.ipcRenderer.send('set-ignore-mouse-events', true);
      } else {
        window.ipcRenderer.send('set-ignore-mouse-events', false);
        window.ipcRenderer.send('wake-up');
      }
    }
  }, [state]);

  useEffect(() => {
    let reconnectTimeout;
    let reconnectDelay = 1000;
    let isUnmounted = false;
    
    const connect = () => {
      if (isUnmounted) return;
      const ws = new WebSocket('ws://localhost:8000/ws');
      wsRef.current = ws;
      
      ws.onopen = () => {
        if (isUnmounted) return;
        console.log('Connected to JARVIS Engine');
        reconnectDelay = 1000;
        ws.send(JSON.stringify({ action: 'ui_ready' }));
      };

      ws.onmessage = (event) => {
        if (isUnmounted) return;
        const message = JSON.parse(event.data);
        if (message.type === 'state_change') {
          setState(message.state);
          setStatusText(message.text || '');
          if (message.subtitle !== undefined) {
            setSubtitle(message.subtitle);
          }
        } else if (message.type === 'play_audio') {
          const audio = new Audio("data:audio/mp3;base64," + message.audio_data);
          setState('speaking');
          setStatusText('SPEAKING');
          setSubtitle(message.text || '');
          
          stopAudioVisualizer(); 
          
          // Randomize audio levels for TTS speaking dynamically
          let ttsInterval = setInterval(() => {
             setAudioLevels(Array.from({length: 12}, () => Math.max(0.1, Math.random() * 0.9)));
          }, 80);

          audio.play();
          audio.onended = () => {
            clearInterval(ttsInterval);
            setAudioLevels(Array(12).fill(0.1));
            
            if (message.text === "Going back to standby mode, Boss.") {
              setState('idle');
              setStatusText('STANDBY');
              setSubtitle('');
              // Small delay before completely hiding to let animation finish
              hideDelayRef.current = setTimeout(() => {
                setState('hidden');
              }, 1500);
            } else {
              // Continuous Conversation Mode: Always keep listening
              wsRef.current.send(JSON.stringify({ action: 'start_listening' }));
            }
          };
        }
      };

      ws.onclose = () => {
        if (isUnmounted) return;
        console.log(`Disconnected from Engine. Reconnecting in ${reconnectDelay}ms`);
        setState('hidden');
        reconnectTimeout = setTimeout(connect, reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
      };
    };

    connect();

    return () => {
      isUnmounted = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
      clearStandbyTimer();
      stopAudioVisualizer();
    };
  }, []);

  return (
    <>
      <div className={`jarvis-container state-${state}`}>
        <div className="drag-handle" />
        
        <div className="hologram-wrapper">
          <div className="ring ring-outer"></div>
          <div className="ring ring-middle"></div>
          <div className="ring ring-inner"></div>
          
          <div className="particles">
            {Array.from({length: 8}).map((_, i) => (
              <div key={i} className={`particle p${i+1}`}></div>
            ))}
          </div>
          
          {/* Circular Visualizer around the orb */}
          <div className={`circular-visualizer ${(state === 'listening' || state === 'speaking') ? 'active' : ''}`}>
            {audioLevels.map((level, i) => {
              const angle = (i / 12) * 360;
              return (
                <div 
                  key={i} 
                  className="bar" 
                  style={{ 
                    transform: `rotate(${angle}deg) translateY(-85px)`,
                    height: `${level * 40 + 5}px` 
                  }}
                ></div>
              );
            })}
          </div>
          
          <div className="orb-core" onClick={() => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ action: 'wake_word' }));
            }
          }} style={{cursor: 'pointer'}}>
            <div className="orb-glow"></div>
            <div className="orb-inner"></div>
          </div>
        </div>
        
        <div className="hologram-base"></div>
        
        <div className="text-container">
          <div className="status-text">{statusText}</div>
          {subtitle && <div className="subtitle-text">{subtitle}</div>}
        </div>
      </div>
    </>
  );
}

export default App;
