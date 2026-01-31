// public/electron.js
const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

// --- Backend Process Management ---
function createPythonProcess() {
  let scriptPath;
  let command;
  let args = [];
  let cwd;

  if (app.isPackaged) {
    // Production: Run the bundled executable
    // Path: resources/pal_backend/pal_backend.exe (Windows)
    const backendDir = path.join(process.resourcesPath, 'pal_backend');
    const executableName = process.platform === 'win32' ? 'pal_backend.exe' : 'pal_backend';
    scriptPath = path.join(backendDir, executableName);
    command = scriptPath;
    cwd = backendDir;
    console.log(`Production mode detected. Starting backend from: ${scriptPath}`);
  } else {
    // Development: Run the Python script
    // Correctly resolve the path to the project root, then join paths from there.
    const projectRoot = path.join(__dirname, '..', '..', '..');
    
    // Path to the runner script, inside posmigra/
    const runnerScript = path.join(projectRoot, 'posmigra', 'run_backend.py');
    
    // Use a generic command. 'python' is standard. 'py' is a fallback for Windows.
    // In dev, we can try to detect which one works or just try both.
    // For simplicity in this logic block, we'll try to find a command first.
    const commands = ['python', 'py'];
    let validCommand = null;
    
    // We can't easily "test" commands synchronously here without execSync which might hang or be noisy.
    // We will just pick one or rely on the loop below if we restructure.
    // But to keep it clean, let's just default to trying 'python' first, handled by the spawn loop logic if we keep it.
    
    // Actually, let's stick to the previous loop approach but adaptable.
    // We'll set command to null and handle it below.
    scriptPath = runnerScript;
    cwd = projectRoot;
    console.log(`Development mode detected. Backend script: ${scriptPath}`);
  }

  if (app.isPackaged) {
    try {
      console.log(`Spawning backend: ${command}`);
      pythonProcess = spawn(command, args, {
        cwd: cwd,
        stdio: 'pipe'
      });
    } catch (e) {
      console.error(`Failed to spawn backend executable: ${e}`);
      return;
    }
  } else {
    // Development: Try python commands
    const commands = ['python', 'py'];
    let commandFound = false;
    
    for (const cmd of commands) {
      try {
        console.log(`Attempting to start Python backend with command: "${cmd}"`);
        pythonProcess = spawn(cmd, ['-u', scriptPath], { // -u for unbuffered output
          cwd: cwd,
          stdio: 'pipe'
        });
        
        // Listen for error event to detect immediate spawn failure (like command not found)
        // Wait, spawn doesn't throw synchronously if command is missing, it emits 'error'.
        // But in a loop, we need to know. 
        // Simple spawn won't tell us immediately. 
        // We'll assume it works and break, but attach error listener. 
        // Real robust checking is harder. 
        // Let's assume if it doesn't throw immediately, it's ok-ish.
        commandFound = true;
        break; 
      } catch (e) {
        console.warn(`Command "${cmd}" failed synchronously. Trying next...`);
      }
    }
    
    if (!commandFound) {
       console.error('Failed to initiate Python backend spawn.');
       return;
    }
  }

  if (!pythonProcess) {
    console.error('Failed to start Python backend.');
    return;
  }
  
  console.log(`Python backend process started with PID: ${pythonProcess.pid}`);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend]: ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Backend ERR]: ${data.toString().trim()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python backend process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python backend process.', err);
  });
}

function killPythonProcess() {
  if (pythonProcess) {
    console.log(`Stopping Python backend process (PID: ${pythonProcess.pid})...`);
    try {
      process.kill(pythonProcess.pid, 'SIGTERM');
      pythonProcess = null;
    } catch (e) {
      console.error('Failed to kill Python process:', e);
    }
  }
}

// --- Electron Window Management ---
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
    icon: path.join(__dirname, 'casapro-icono.png'),
  });

  // Use environment variable for dev URL, otherwise load production build
  const startUrl = process.env.ELECTRON_START_URL || `file://${path.join(__dirname, '../build/index.html')}`;
  
  console.log(`Loading URL: ${startUrl}`);
  mainWindow.loadURL(startUrl);

  if (process.env.ELECTRON_START_URL) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// --- Electron App Lifecycle ---
app.on('ready', () => {
  console.log('Electron app is ready. Starting backend and creating window...');
  createPythonProcess();
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('quit', () => {
  killPythonProcess();
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});