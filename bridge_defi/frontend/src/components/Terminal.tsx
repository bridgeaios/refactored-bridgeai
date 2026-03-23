// Digital Twin Terminal Component
// Embedded terminal using xterm.js for executing code and commands

import { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface TerminalProps {
  wsUrl?: string;
  onCommand?: (cmd: string) => void;
}

export default function Terminal({ wsUrl = 'ws://localhost:8000/ws/terminal', onCommand }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const historyIndex = useRef(-1);

  useEffect(() => {
    if (!terminalRef.current) return;

    const term = new XTerm({
      theme: {
        background: '#0a0a0f',
        foreground: '#00ff88',
        cursor: '#00ff88',
        cursorAccent: '#0a0a0f',
        selectionBackground: 'rgba(0, 255, 136, 0.3)',
        black: '#000000',
        red: '#ff4444',
        green: '#00ff88',
        yellow: '#ffff00',
        blue: '#4444ff',
        magenta: '#ff00ff',
        cyan: '#00ffff',
        white: '#ffffff',
      },
      fontFamily: '"Fira Code", "JetBrains Mono", monospace',
      fontSize: 14,
      lineHeight: 1.2,
      cursorBlink: true,
      cursorStyle: 'block',
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;

    // Welcome message
    term.writeln('\x1b[36m╔════════════════════════════════════════════════════════╗\x1b[0m');
    term.writeln('\x1b[36m║\x1b[0m   \x1b[1;32mDIGITAL TWIN TERMINAL v1.0\x1b[0m                          \x1b[36m║\x1b[0m');
    term.writeln('\x1b[36m║\x1b[0m   Autonomous AI Agent Execution Environment        \x1b[36m║\x1b[0m');
    term.writeln('\x1b[36m╚════════════════════════════════════════════════════════╝\x1b[0m');
    term.writeln('');
    term.writeln('\x1b[33mAvailable commands:\x1b[0m');
    term.writeln('  \x1b[32mtasks\x1b[0m     - List all tasks in the system');
    term.writeln('  \x1b[32mskills\x1b[0m    - List all available skills');
    term.writeln('  \x1b[32mdeploy\x1b[0m   - Deploy autonomous apps');
    term.writeln('  \x1b[32mstatus\x1b[0m   - Show system status');
    term.writeln('  \x1b[32mhelp\x1b[0m     - Show this help');
    term.writeln('');
    term.write('\x1b[32m❯\x1b[0m ');

    // Handle user input
    let currentLine = '';
    
    term.onData((data) => {
      const code = data.charCodeAt(0);
      
      if (code === 13) { // Enter
        term.writeln('');
        if (currentLine.trim()) {
          setCommandHistory(prev => [...prev, currentLine]);
          historyIndex.current = commandHistory.length;
          
          // Execute command locally first
          handleCommand(currentLine.trim(), term);
          
          // Also send to WebSocket if connected
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'command', data: currentLine }));
          }
          
          if (onCommand) onCommand(currentLine);
        }
        currentLine = '';
        term.write('\x1b[32m❯\x1b[0m ');
      } else if (code === 127) { // Backspace
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          term.write('\b \b');
        }
      } else if (code === 27) { // Arrow keys
        // Handle arrow keys for history
        if (data === '\x1b[A') { // Up
          if (historyIndex.current > 0) {
            historyIndex.current--;
            clearLine(term, currentLine);
            currentLine = commandHistory[historyIndex.current] || '';
            term.write(currentLine);
          }
        } else if (data === '\x1b[B') { // Down
          if (historyIndex.current < commandHistory.length - 1) {
            historyIndex.current++;
            clearLine(term, currentLine);
            currentLine = commandHistory[historyIndex.current] || '';
            term.write(currentLine);
          } else {
            historyIndex.current = commandHistory.length;
            clearLine(term, currentLine);
            currentLine = '';
          }
        }
      } else if (code >= 32) { // Printable characters
        currentLine += data;
        term.write(data);
      }
    });

    // Connect WebSocket
    try {
      setStatus('connecting');
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        setStatus('connected');
        term.writeln('\x1b[32m[WS] Connected to Digital Twin\x1b[0m');
      };
      
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'output') {
            term.writeln(msg.data);
          } else if (msg.type === 'error') {
            term.writeln(`\x1b[31m[ERROR] ${msg.data}\x1b[0m`);
          }
        } catch {
          term.writeln(event.data);
        }
      };
      
      ws.onclose = () => {
        setStatus('disconnected');
        term.writeln('\x1b[33m[WS] Disconnected from Digital Twin\x1b[0m');
      };
      
      ws.onerror = () => {
        setStatus('disconnected');
      };
      
      wsRef.current = ws;
    } catch {
      // WebSocket connection failed, continue in local mode
    }

    // Handle resize
    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      wsRef.current?.close();
      term.dispose();
    };
  }, []);

  const clearLine = (term: XTerm, line: string) => {
    for (let i = 0; i < line.length; i++) {
      term.write('\b \b');
    }
  };

  const handleCommand = (cmd: string, term: XTerm) => {
    const parts = cmd.toLowerCase().split(/\s+/);
    const command = parts[0];
    const args = parts.slice(1);

    switch (command) {
      case 'help':
        term.writeln('\x1b[33mAvailable commands:\x1b[0m');
        term.writeln('  \x1b[32mtasks\x1b[0m     - List all tasks');
        term.writeln('  \x1b[32mskills\x1b[0m    - List all skills');
        term.writeln('  \x1b[32mdeploy\x1b[0m   - Deploy 50 autonomous apps');
        term.writeln('  \x1b[32mstatus\x1b[0m   - Show system status');
        term.writeln('  \x1b[32mclear\x1b[0m    - Clear terminal');
        term.writeln('  \x1b[32mhelp\x1b[0m     - Show this help');
        break;
        
      case 'clear':
        term.clear();
        break;
        
      case 'tasks':
        term.writeln('\x1b[36mFetching tasks...\x1b[0m');
        fetch('/api/tasks')
          .then(r => r.json())
          .then(data => {
            if (Array.isArray(data) && data.length > 0) {
              term.writeln(`\x1b[32mFound ${data.length} tasks:\x1b[0m`);
              data.slice(0, 10).forEach((t: any, i: number) => {
                term.writeln(`  ${i + 1}. ${t.title || t.name || 'Unnamed'} [${t.status || 'unknown'}]`);
              });
              if (data.length > 10) term.writeln(`  ... and ${data.length - 10} more`);
            } else {
              term.writeln('\x1b[33mNo tasks found\x1b[0m');
            }
          })
          .catch(e => term.writeln(`\x1b[31mError: ${e.message}\x1b[0m`));
        break;
        
      case 'skills':
        term.writeln('\x1b[36mFetching skills...\x1b[0m');
        fetch('/api/skills')
          .then(r => r.json())
          .then(data => {
            if (Array.isArray(data) && data.length > 0) {
              term.writeln(`\x1b[32mFound ${data.length} skills:\x1b[0m`);
              data.slice(0, 20).forEach((s: any, i: number) => {
                term.writeln(`  ${i + 1}. ${s.name} [${s.category || 'general'}]`);
              });
              if (data.length > 20) term.writeln(`  ... and ${data.length - 20} more`);
            } else {
              term.writeln('\x1b[33mNo skills found - run scan first\x1b[0m');
            }
          })
          .catch(e => term.writeln(`\x1b[31mError: ${e.message}\x1b[0m`));
        break;
        
      case 'deploy':
        term.writeln('\x1b[36m🚀 Starting autonomous deployment of 50 apps...\x1b[0m');
        term.writeln('\x1b[33mThis may take a few minutes. Progress will be shown below.\x1b[0m');
        
        fetch('/api/autonomous/deploy-50-apps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        .then(r => r.json())
        .then(data => {
          term.writeln(`\x1b[32m✓ Deployment complete!\x1b[0m`);
          term.writeln(`  Deployed: ${data.deployed_count || data.applications?.length || 0} apps`);
          if (data.applications) {
            data.applications.slice(0, 5).forEach((app: any) => {
              term.writeln(`    • ${app.title}`);
            });
            if (data.applications.length > 5) {
              term.writeln(`    ... and ${data.applications.length - 5} more`);
            }
          }
        })
        .catch(e => term.writeln(`\x1b[31mError: ${e.message}\x1b[0m`));
        break;
        
      case 'status':
        term.writeln('\x1b[36mDigital Twin System Status\x1b[0m');
        term.writeln('─'.repeat(40));
        
        Promise.all([
          fetch('/api/health').then(r => r.json()).catch(() => ({ status: 'error' })),
          fetch('/api/tasks').then(r => r.json()).then(d => d.length || 0).catch(() => 0),
          fetch('/api/skills').then(r => r.json()).then(d => d.length || 0).catch(() => 0),
        ])
        .then(([health, taskCount, skillCount]) => {
          term.writeln(`  \x1b[32mStatus:\x1b[0m ${health.status || 'healthy'}`);
          term.writeln(`  \x1b[32mTasks:\x1b[0m ${taskCount}`);
          term.writeln(`  \x1b[32mSkills:\x1b[0m ${skillCount}`);
          term.writeln(`  \x1b[32mTerminal:\x1b[0m ${status}`);
        });
        break;
        
      default:
        term.writeln(`\x1b[31mUnknown command: ${command}\x1b[0m`);
        term.writeln('\x1b[33mType "help" for available commands\x1b[0m');
    }
  };

  return (
    <div className="terminal-container" style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#0a0a0f',
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: '#151520',
        borderBottom: '1px solid #2a2a3a'
      }}>
        <span style={{ color: '#888', fontSize: '12px' }}>
          Digital Twin Terminal
        </span>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: status === 'connected' ? '#00ff88' : status === 'connecting' ? '#ffff00' : '#ff4444'
          }} />
          <span style={{ color: '#666', fontSize: '11px' }}>
            {status}
          </span>
        </div>
      </div>
      <div 
        ref={terminalRef} 
        style={{ flex: 1, padding: '8px' }}
      />
    </div>
  );
}
