import React, { useState, useEffect, useRef } from 'react';
import { 
  Briefcase, Plus, Play, ShieldAlert, BadgeAlert, CheckCircle2, 
  MessageSquare, LayoutDashboard, ListTodo, Calendar, LogOut, 
  Send, RefreshCw, Trash2, Edit2, CheckSquare, Square, ChevronDown, 
  ChevronRight, Sparkles, User, Lock, AlertTriangle, Eye, Download, Info
} from 'lucide-react';

// API Configuration
const API_BASE = ''; // Proxied by Vite in dev, same domain in production

// Interfaces
interface UserInfo {
  username: string;
  role: string;
}

interface Project {
  id: string;
  name: string;
  concept: string;
  status: string;
  theme: string;
  workspace_path: string;
  created_at: string;
}

interface BuildTask {
  id: number;
  phase: string;
  task_name: string;
  status: string;
  completed_at: string | null;
}

interface UserStory {
  id: number;
  project_id: string;
  sprint_id: number | null;
  title: string;
  description: string;
  persona: string | null;
  want: string | null;
  benefit: string | null;
  acceptance_criteria: string | null;
  priority: string;
  business_value: number;
  technical_risk: number;
  story_points: number | null;
  complexity_rationale: string | null;
  status: string; // backlog, todo, in_progress, done
}

interface DevTask {
  id: number;
  story_id: number;
  task_type: string; // Database, API, Frontend, QA
  task_name: string;
  description: string | null;
  estimated_hours: number;
  status: string; // todo, done
}

interface Sprint {
  id: number;
  project_id: string;
  name: string;
  goal: string | null;
  start_date: string | null;
  end_date: string | null;
  status: string; // planning, active, completed
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function App() {
  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [user, setUser] = useState<UserInfo | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authRole, setAuthRole] = useState('PO');
  const [authError, setAuthError] = useState('');

  // Core App State
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [currentView, setCurrentView] = useState<'dashboard' | 'backlog' | 'sprint' | 'chat'>('dashboard');
  const [isInitializingProject, setIsInitializingProject] = useState(false);

  // New Project Form
  const [newProjName, setNewProjName] = useState('');
  const [newProjConcept, setNewProjConcept] = useState('');

  // Selected Project Status
  const [projectStatus, setProjectStatus] = useState<any>(null);
  const [isPollingStatus, setIsPollingStatus] = useState(false);

  // Backlog state
  const [stories, setStories] = useState<UserStory[]>([]);
  const [isGeneratingStories, setIsGeneratingStories] = useState(false);
  const [isPrioritizing, setIsPrioritizing] = useState(false);
  const [newStoryTitle, setNewStoryTitle] = useState('');
  const [newStoryPersona, setNewStoryPersona] = useState('');
  const [newStoryWant, setNewStoryWant] = useState('');
  const [newStoryBenefit, setNewStoryBenefit] = useState('');
  const [newStoryAC, setNewStoryAC] = useState('');
  const [showAddStoryForm, setShowAddStoryForm] = useState(false);
  
  // Story Edit Modal
  const [editingStory, setEditingStory] = useState<UserStory | null>(null);
  const [editStoryTitle, setEditStoryTitle] = useState('');
  const [editStoryDesc, setEditStoryDesc] = useState('');
  const [editStoryAC, setEditStoryAC] = useState('');
  const [editStoryPriority, setEditStoryPriority] = useState('Should');
  const [editStoryPoints, setEditStoryPoints] = useState<number>(3);
  const [editStoryStatus, setEditStoryStatus] = useState('backlog');

  // Dev tasks states
  const [storyTasks, setStoryTasks] = useState<Record<number, DevTask[]>>({});
  const [loadingTasksStoryId, setLoadingTasksStoryId] = useState<number | null>(null);

  // Sprints state
  const [sprints, setSprints] = useState<Sprint[]>([]);
  const [newSprintName, setNewSprintName] = useState('');
  const [newSprintGoal, setNewSprintGoal] = useState('');
  const [showAddSprintForm, setShowAddSprintForm] = useState(false);

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', content: 'Chào bạn! Tôi là Product Owner Agent. Hãy hỏi tôi về yêu cầu dự án, cách viết user story, phân chia sprint hoặc thiết lập các task phát triển nhé!' }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // API wrapper
  const apiFetch = async (endpoint: string, options: any = {}) => {
    const headers = new Headers(options.headers || {});
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
    
    // Default to JSON body if object is passed
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
      options.body = JSON.stringify(options.body);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    
    if (response.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'API request failed');
    }

    return response.json();
  };

  // Auth Effects
  useEffect(() => {
    if (token) {
      apiFetch('/api/auth/me')
        .then(userData => {
          setUser(userData);
          fetchProjects();
        })
        .catch(() => {
          localStorage.removeItem('token');
          setToken(null);
        });
    }
  }, [token]);

  // Project Selection Effect
  useEffect(() => {
    if (selectedProjectId) {
      fetchProjectStatus();
      fetchStories();
      fetchSprints();
    } else {
      setProjectStatus(null);
      setStories([]);
      setSprints([]);
    }
  }, [selectedProjectId]);

  // Chat scroll effect
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Background status polling during builds
  useEffect(() => {
    let intervalId: any;
    if (selectedProjectId && isPollingStatus) {
      intervalId = setInterval(() => {
        fetchProjectStatus(true);
      }, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [selectedProjectId, isPollingStatus]);

  // Core Data Fetchers
  const fetchProjects = async () => {
    try {
      const projs = await apiFetch('/api/projects');
      setProjects(projs);
      if (projs.length > 0 && !selectedProjectId) {
        setSelectedProjectId(projs[0].id);
      }
    } catch (e) {
      console.error("Failed to load projects", e);
    }
  };

  const fetchProjectStatus = async (isPoll = false) => {
    if (!selectedProjectId) return;
    try {
      const statusData = await apiFetch(`/api/project/${selectedProjectId}/status`);
      setProjectStatus(statusData);
      
      // Stop polling if build completed/failed
      const overallStatus = statusData.project.status;
      if (overallStatus !== 'BUILDING' && overallStatus !== 'QUEUED') {
        setIsPollingStatus(false);
      } else {
        setIsPollingStatus(true);
      }
    } catch (e) {
      console.error("Failed to fetch project status", e);
      if (isPoll) setIsPollingStatus(false);
    }
  };

  const fetchStories = async () => {
    if (!selectedProjectId) return;
    try {
      const storyData = await apiFetch(`/api/po/projects/${selectedProjectId}/stories`);
      setStories(storyData);
      
      // Prefetch dev tasks for stories that are not in backlog
      storyData.forEach((s: UserStory) => {
        if (s.status !== 'backlog') {
          fetchDevTasks(s.id);
        }
      });
    } catch (e) {
      console.error("Failed to fetch stories", e);
    }
  };

  const fetchSprints = async () => {
    if (!selectedProjectId) return;
    try {
      const sprintData = await apiFetch(`/api/po/projects/${selectedProjectId}/sprints`);
      setSprints(sprintData);
    } catch (e) {
      console.error("Failed to fetch sprints", e);
    }
  };

  const fetchDevTasks = async (storyId: number) => {
    try {
      const tasks = await apiFetch(`/api/po/stories/${storyId}/tasks`);
      setStoryTasks(prev => ({ ...prev, [storyId]: tasks }));
    } catch (e) {
      console.error("Failed to fetch dev tasks", e);
    }
  };

  // Auth handlers
  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    try {
      if (authMode === 'login') {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: authUsername, password: authPassword })
        });
        if (!res.ok) throw new Error('Sai tên đăng nhập hoặc mật khẩu');
        const data = await res.json();
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);
      } else {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: authUsername, password: authPassword, role: authRole })
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          throw new Error(detail.detail || 'Không thể đăng ký tài khoản');
        }
        setAuthMode('login');
        setAuthPassword('');
        setAuthError('Đăng ký thành công! Hãy đăng nhập.');
      }
    } catch (err: any) {
      setAuthError(err.message || 'Lỗi kết nối API');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setSelectedProjectId('');
    setProjects([]);
  };

  // Project Handlers
  const handleInitProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName || !newProjConcept) return;
    setIsInitializingProject(true);
    try {
      const res = await apiFetch('/api/project/init', {
        method: 'POST',
        body: { name: newProjName, concept: newProjConcept }
      });
      setNewProjName('');
      setNewProjConcept('');
      await fetchProjects();
      setSelectedProjectId(res.project_id);
      setCurrentView('dashboard');
    } catch (err: any) {
      alert(`Initialization failed: ${err.message}`);
    } finally {
      setIsInitializingProject(false);
    }
  };

  const handleTriggerBuild = async () => {
    if (!selectedProjectId) return;
    try {
      await apiFetch(`/api/project/build/${selectedProjectId}`, { method: 'POST' });
      setIsPollingStatus(true);
      fetchProjectStatus();
    } catch (err: any) {
      alert(`Build trigger failed: ${err.message}`);
    }
  };

  const handleTriggerForensics = async () => {
    if (!selectedProjectId) return;
    try {
      alert("Đang kích hoạt quy trình Forensics Agent (Self-healing). Tiến trình này sẽ chạy trực tiếp Playwright và chẩn đoán sửa lỗi...");
      const result = await apiFetch(`/api/project/forensics/${selectedProjectId}`, { method: 'POST' });
      alert(result.message || "Forensics hoàn tất thành công.");
      fetchProjectStatus();
    } catch (err: any) {
      alert(`Forensics failed: ${err.message}`);
    }
  };

  // Backlog Handlers
  const handleGenerateStories = async () => {
    if (!selectedProjectId) return;
    setIsGeneratingStories(true);
    try {
      await apiFetch('/api/po/stories/generate', {
        method: 'POST',
        body: { project_id: selectedProjectId }
      });
      fetchStories();
    } catch (err: any) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      setIsGeneratingStories(false);
    }
  };

  const handlePrioritizeBacklog = async () => {
    if (!selectedProjectId) return;
    setIsPrioritizing(true);
    try {
      await apiFetch('/api/po/stories/prioritize-estimate', {
        method: 'POST',
        body: { project_id: selectedProjectId }
      });
      fetchStories();
    } catch (err: any) {
      alert(`Prioritization and Estimation failed: ${err.message}`);
    } finally {
      setIsPrioritizing(false);
    }
  };

  const handleCreateStory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStoryTitle) return;
    try {
      await apiFetch(`/api/po/projects/${selectedProjectId}/stories`, {
        method: 'POST',
        body: {
          title: newStoryTitle,
          persona: newStoryPersona,
          want: newStoryWant,
          benefit: newStoryBenefit,
          acceptance_criteria: newStoryAC
        }
      });
      setNewStoryTitle('');
      setNewStoryPersona('');
      setNewStoryWant('');
      setNewStoryBenefit('');
      setNewStoryAC('');
      setShowAddStoryForm(false);
      fetchStories();
    } catch (err: any) {
      alert(`Create story failed: ${err.message}`);
    }
  };

  const handleDeleteStory = async (storyId: number) => {
    if (!confirm("Bạn có chắc chắn muốn xóa story này?")) return;
    try {
      await apiFetch(`/api/po/stories/${storyId}`, { method: 'DELETE' });
      fetchStories();
    } catch (err: any) {
      alert(`Delete story failed: ${err.message}`);
    }
  };

  const handleBreakdownTasks = async (storyId: number) => {
    setLoadingTasksStoryId(storyId);
    try {
      await apiFetch(`/api/po/stories/${storyId}/breakdown`, { method: 'POST' });
      await fetchDevTasks(storyId);
    } catch (err: any) {
      alert(`Task breakdown failed: ${err.message}`);
    } finally {
      setLoadingTasksStoryId(null);
    }
  };

  const handleToggleTask = async (taskId: number, currentStatus: string, storyId: number) => {
    const nextStatus = currentStatus === 'done' ? 'todo' : 'done';
    try {
      await apiFetch(`/api/po/tasks/${taskId}/status`, {
        method: 'PUT',
        body: { status: nextStatus }
      });
      fetchDevTasks(storyId);
    } catch (err: any) {
      alert(`Task update failed: ${err.message}`);
    }
  };

  const handleUpdateStoryStatus = async (storyId: number, statusStr: string) => {
    try {
      await apiFetch(`/api/po/stories/${storyId}/status`, {
        method: 'PUT',
        body: { status: statusStr }
      });
      fetchStories();
    } catch (err: any) {
      alert(`Status update failed: ${err.message}`);
    }
  };

  const handleSprintAddStory = async (sprintId: number, storyId: number) => {
    try {
      await apiFetch(`/api/po/sprints/${sprintId}/add-story/${storyId}`, { method: 'POST' });
      fetchStories();
    } catch (err: any) {
      alert(`Assign story to sprint failed: ${err.message}`);
    }
  };

  // Edit Story Modal Actions
  const openEditModal = (story: UserStory) => {
    setEditingStory(story);
    setEditStoryTitle(story.title);
    setEditStoryDesc(story.description);
    setEditStoryAC(story.acceptance_criteria || '');
    setEditStoryPriority(story.priority);
    setEditStoryPoints(story.story_points || 3);
    setEditStoryStatus(story.status);
  };

  const handleSaveStoryEdit = async () => {
    if (!editingStory) return;
    try {
      await apiFetch(`/api/po/stories/${editingStory.id}`, {
        method: 'PUT',
        body: {
          title: editStoryTitle,
          description: editStoryDesc,
          acceptance_criteria: editStoryAC,
          priority: editStoryPriority,
          story_points: editStoryPoints,
          status: editStoryStatus
        }
      });
      setEditingStory(null);
      fetchStories();
    } catch (err: any) {
      alert(`Failed to save story edit: ${err.message}`);
    }
  };

  // Sprint Creation
  const handleCreateSprint = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSprintName) return;
    try {
      await apiFetch(`/api/po/projects/${selectedProjectId}/sprints`, {
        method: 'POST',
        body: { name: newSprintName, goal: newSprintGoal }
      });
      setNewSprintName('');
      setNewSprintGoal('');
      setShowAddSprintForm(false);
      fetchSprints();
    } catch (err: any) {
      alert(`Sprint creation failed: ${err.message}`);
    }
  };

  // Chat Handler
  const handleSendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setIsChatLoading(true);

    try {
      // Exclude greeting message from historical prompts to keep context clean
      const history = chatMessages
        .slice(1)
        .map(msg => ({ role: msg.role, content: msg.content }));

      const res = await apiFetch('/api/po/chat', {
        method: 'POST',
        body: { message: userMsg, history }
      });

      setChatMessages(prev => [...prev, { role: 'assistant', content: res.response }]);
    } catch (err: any) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: `Lỗi kết nối LLM: ${err.message}` }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Authentication Guard Render
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 relative">
        {/* Glow ambient backgrounds */}
        <div className="absolute w-[300px] h-[300px] rounded-full bg-rosegold-glow filter blur-[60px] top-[10%] left-[20%] pointer-events-none"></div>
        <div className="absolute w-[300px] h-[300px] rounded-full bg-cyber-cyanGlow filter blur-[60px] bottom-[10%] right-[20%] pointer-events-none"></div>
        
        <div className="glass-panel w-full max-w-md p-8 rounded-2xl border border-obsidian-border shadow-glow-rose relative overflow-hidden">
          <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-rosegold to-cyber-cyan"></div>
          
          <div className="text-center mb-8">
            <div className="inline-flex p-3 rounded-full bg-rosegold-glow text-rosegold mb-4">
              <Sparkles className="w-8 h-8" />
            </div>
            <h1 className="text-3xl font-black tracking-tight text-obsidian-textBright">Web AI Platform</h1>
            <p className="text-obsidian-text text-sm mt-1">Autonomous Multi-Agent & Skill Server</p>
          </div>

          <form onSubmit={handleAuthSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-obsidian-textBright uppercase tracking-wider mb-2">Username</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-obsidian-text">
                  <User className="w-4 h-4" />
                </span>
                <input 
                  type="text" 
                  required
                  value={authUsername}
                  onChange={(e) => setAuthUsername(e.target.value)}
                  className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg py-2.5 pl-10 pr-4 text-obsidian-textBright focus:outline-none focus:border-rosegold transition-colors placeholder-obsidian-text/40 text-sm"
                  placeholder="Nhập tên đăng nhập..."
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-obsidian-textBright uppercase tracking-wider mb-2">Password</label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-obsidian-text">
                  <Lock className="w-4 h-4" />
                </span>
                <input 
                  type="password" 
                  required
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg py-2.5 pl-10 pr-4 text-obsidian-textBright focus:outline-none focus:border-rosegold transition-colors placeholder-obsidian-text/40 text-sm"
                  placeholder="Nhập mật khẩu..."
                />
              </div>
            </div>

            {authMode === 'register' && (
              <div>
                <label className="block text-xs font-semibold text-obsidian-textBright uppercase tracking-wider mb-2">System Role</label>
                <select 
                  value={authRole}
                  onChange={(e) => setAuthRole(e.target.value)}
                  className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg py-2.5 px-4 text-obsidian-textBright focus:outline-none focus:border-rosegold transition-colors text-sm"
                >
                  <option value="PO">Product Owner (PO)</option>
                  <option value="Admin">Administrator</option>
                </select>
              </div>
            )}

            {authError && (
              <div className={`p-3 rounded-lg text-xs flex items-center gap-2 ${authError.includes('thành công') ? 'bg-cyber-green/10 text-cyber-green border border-cyber-green/20' : 'bg-cyber-red/10 text-cyber-red border border-cyber-red/20'}`}>
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            <button 
              type="submit"
              className="w-full bg-gradient-to-r from-rosegold to-rosegold-dark hover:from-rosegold-dark hover:to-rosegold text-obsidian-bg font-bold py-3 rounded-lg shadow-glow-rose hover:scale-[1.01] active:scale-[0.99] transition-all text-sm mt-6"
            >
              {authMode === 'login' ? 'Đăng Nhập' : 'Đăng Ký Tài Khoản'}
            </button>
          </form>

          <div className="text-center mt-6">
            <button 
              onClick={() => {
                setAuthMode(authMode === 'login' ? 'register' : 'login');
                setAuthError('');
              }}
              className="text-xs text-rosegold hover:underline"
            >
              {authMode === 'login' ? 'Chưa có tài khoản? Đăng ký ngay' : 'Đã có tài khoản? Quay về đăng nhập'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Layout & Main App Render
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Header */}
      <header className="glass-panel border-b border-obsidian-border px-6 py-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-gradient-to-br from-rosegold to-cyber-cyan text-obsidian-bg">
              <Sparkles className="w-5 h-5" />
            </div>
            <span className="text-lg font-black tracking-wider text-obsidian-textBright uppercase">AI Web Platform</span>
          </div>

          {/* Project Selector */}
          {projects.length > 0 && (
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-rosegold" />
              <div className="relative">
                <select 
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="bg-obsidian-bg border border-obsidian-border rounded-lg py-1.5 pl-3 pr-8 text-obsidian-textBright font-semibold text-xs focus:outline-none focus:border-rosegold cursor-pointer appearance-none"
                >
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-obsidian-text absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>
          )}
        </div>

        {/* Center navigation tabs */}
        <nav className="flex items-center gap-1 bg-obsidian-bg/50 p-1 rounded-lg border border-obsidian-border">
          <button 
            onClick={() => setCurrentView('dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all ${currentView === 'dashboard' ? 'bg-rosegold text-obsidian-bg shadow-glow-rose' : 'text-obsidian-text hover:text-obsidian-textBright'}`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Control Center</span>
          </button>
          <button 
            onClick={() => setCurrentView('backlog')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all ${currentView === 'backlog' ? 'bg-rosegold text-obsidian-bg shadow-glow-rose' : 'text-obsidian-text hover:text-obsidian-textBright'}`}
          >
            <ListTodo className="w-4 h-4" />
            <span>Agile Backlog</span>
          </button>
          <button 
            onClick={() => setCurrentView('sprint')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all ${currentView === 'sprint' ? 'bg-rosegold text-obsidian-bg shadow-glow-rose' : 'text-obsidian-text hover:text-obsidian-textBright'}`}
          >
            <Calendar className="w-4 h-4" />
            <span>Sprint Board</span>
          </button>
          <button 
            onClick={() => setCurrentView('chat')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all ${currentView === 'chat' ? 'bg-rosegold text-obsidian-bg shadow-glow-rose' : 'text-obsidian-text hover:text-obsidian-textBright'}`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>PO Chat</span>
          </button>
        </nav>

        {/* User control */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-obsidian-hover flex items-center justify-center text-rosegold font-bold border border-obsidian-border text-xs">
              {user?.username?.substring(0, 2).toUpperCase()}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-xs font-bold text-obsidian-textBright">{user?.username}</p>
              <p className="text-[9px] text-obsidian-text uppercase tracking-wider">{user?.role}</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 rounded-lg bg-obsidian-hover border border-obsidian-border text-obsidian-text hover:text-cyber-red transition-all cursor-pointer hover:border-cyber-red/20"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-grow p-6 max-w-7xl w-full mx-auto">
        
        {/* VIEW 1: Control Center Dashboard */}
        {currentView === 'dashboard' && (
          <div className="space-y-6">
            
            {/* Split top pane: Active Project Status & Create New Project */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              
              {/* Project spec block */}
              <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-obsidian-border relative overflow-hidden flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4 border-b border-obsidian-border/50 pb-4">
                    <div>
                      <span className="text-[10px] text-rosegold uppercase tracking-wider font-bold">Dự án hiện hành</span>
                      <h2 className="text-2xl font-black text-obsidian-textBright mt-0.5">
                        {projectStatus?.project?.name || "Chưa có dự án nào"}
                      </h2>
                    </div>
                    {projectStatus?.project && (
                      <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                        projectStatus.project.status === 'PASSED' ? 'bg-cyber-green/10 text-cyber-green border border-cyber-green/20' :
                        projectStatus.project.status === 'FAILED' ? 'bg-cyber-red/10 text-cyber-red border border-cyber-red/20' :
                        projectStatus.project.status === 'BUILDING' || projectStatus.project.status === 'QUEUED' ? 'bg-rosegold/10 text-rosegold border border-rosegold/20 animate-pulse' :
                        'bg-obsidian-hover text-obsidian-text border border-obsidian-border'
                      }`}>
                        {projectStatus.project.status}
                      </span>
                    )}
                  </div>
                  
                  {projectStatus?.project ? (
                    <div className="space-y-3">
                      <div>
                        <p className="text-[10px] uppercase font-bold text-obsidian-text">Mô tả Concept</p>
                        <p className="text-xs text-obsidian-textBright mt-1 bg-obsidian-bg/50 p-3 rounded-lg border border-obsidian-border/30 max-h-[120px] overflow-y-auto leading-relaxed">
                          {projectStatus.project.concept}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-obsidian-text font-medium">Giao diện:</span>
                          <span className="text-obsidian-textBright ml-2 font-semibold">{projectStatus.project.theme}</span>
                        </div>
                        <div>
                          <span className="text-obsidian-text font-medium">Workspace:</span>
                          <span className="text-obsidian-textBright ml-2 font-mono break-all">{projectStatus.project.workspace_path}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-obsidian-text">
                      Hãy tạo một dự án mới ở bảng bên cạnh để bắt đầu.
                    </div>
                  )}
                </div>

                {projectStatus?.project && (
                  <div className="flex flex-wrap gap-3 mt-6 border-t border-obsidian-border/50 pt-4">
                    <button 
                      onClick={handleTriggerBuild}
                      disabled={projectStatus.project.status === 'BUILDING' || projectStatus.project.status === 'QUEUED'}
                      className="flex items-center gap-2 bg-rosegold hover:bg-rosegold-dark disabled:bg-obsidian-hover disabled:text-obsidian-text text-obsidian-bg px-5 py-2.5 rounded-lg text-xs font-black uppercase transition-all shadow-glow-rose hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
                    >
                      <Play className="w-4 h-4 fill-current" />
                      <span>Kích hoạt build 6 Pha</span>
                    </button>
                    {projectStatus.project.status === 'FAILED' && (
                      <button 
                        onClick={handleTriggerForensics}
                        className="flex items-center gap-2 bg-obsidian-hover hover:bg-obsidian-hover/80 text-rosegold border border-rosegold/30 hover:border-rosegold px-5 py-2.5 rounded-lg text-xs font-black uppercase transition-all cursor-pointer"
                      >
                        <RefreshCw className="w-4 h-4 animate-spin-slow" />
                        <span>Chạy Sửa lỗi Tự động (Forensics)</span>
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Create new project block */}
              <div className="glass-panel p-6 rounded-2xl border border-obsidian-border">
                <span className="text-[10px] text-cyber-cyan uppercase tracking-wider font-bold">Khởi tạo</span>
                <h3 className="text-lg font-black text-obsidian-textBright mt-0.5 mb-4">Tạo dự án mới</h3>

                <form onSubmit={handleInitProject} className="space-y-4">
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Tên dự án</label>
                    <input 
                      type="text" 
                      required
                      value={newProjName}
                      onChange={(e) => setNewProjName(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-cyber-cyan transition-colors"
                      placeholder="e.g. My Portfolio"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Yêu cầu nghiệp vụ (Concept / Spec)</label>
                    <textarea 
                      required
                      rows={4}
                      value={newProjConcept}
                      onChange={(e) => setNewProjConcept(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-cyber-cyan transition-colors resize-none"
                      placeholder="e.g. A personal portfolio web app showcasing a obsidian glassmorphic theme. Include page sections for Bio, Projects, Contact form..."
                    />
                  </div>
                  <button 
                    type="submit"
                    disabled={isInitializingProject}
                    className="w-full bg-cyber-cyan text-obsidian-bg font-bold py-2.5 rounded-lg text-xs uppercase shadow-glow-cyan hover:scale-[1.01] active:scale-[0.99] transition-all disabled:bg-obsidian-hover disabled:text-obsidian-text cursor-pointer"
                  >
                    {isInitializingProject ? 'Đang phân tích cấu trúc...' : 'Tạo specs & Khởi dựng'}
                  </button>
                </form>
              </div>

            </div>

            {/* Bottom: 6-Phase Build Progress Tracker */}
            {projectStatus && (
              <div className="glass-panel p-6 rounded-2xl border border-obsidian-border">
                <span className="text-[10px] text-rosegold uppercase tracking-wider font-bold">Quy trình Agent tự động</span>
                <h3 className="text-lg font-black text-obsidian-textBright mt-0.5 mb-6">Trình giám sát 6 Pha tích hợp</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
                  {projectStatus.tasks.map((task: BuildTask, idx: number) => (
                    <div 
                      key={task.id} 
                      className={`p-4 rounded-xl border relative flex flex-col justify-between h-[150px] transition-all ${
                        task.status === 'COMPLETED' ? 'bg-cyber-green/5 border-cyber-green/20 text-cyber-green' :
                        task.status === 'RUNNING' ? 'bg-rosegold/5 border-rosegold/30 text-rosegold animate-pulse-gold' :
                        task.status === 'FAILED' ? 'bg-cyber-red/5 border-cyber-red/20 text-cyber-red' :
                        'bg-obsidian-card/40 border-obsidian-border text-obsidian-text'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <span className="text-[9px] font-bold uppercase tracking-wider bg-obsidian-hover/40 px-1.5 py-0.5 rounded border border-obsidian-border/30">
                          {task.phase}
                        </span>
                        {task.status === 'COMPLETED' && <CheckCircle2 className="w-4 h-4" />}
                        {task.status === 'RUNNING' && <RefreshCw className="w-4 h-4 animate-spin" />}
                        {task.status === 'FAILED' && <BadgeAlert className="w-4 h-4" />}
                      </div>

                      <div className="mt-4">
                        <p className="text-xs font-bold text-obsidian-textBright line-clamp-2">{task.task_name}</p>
                        <span className={`text-[9px] font-black uppercase mt-1 inline-block ${
                          task.status === 'COMPLETED' ? 'text-cyber-green' :
                          task.status === 'RUNNING' ? 'text-rosegold' :
                          task.status === 'FAILED' ? 'text-cyber-red' :
                          'text-obsidian-text'
                        }`}>
                          {task.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Audit & Report Panels */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8 pt-8 border-t border-obsidian-border/50">
                  {/* QA report summary */}
                  <div className="bg-obsidian-card/30 rounded-xl border border-obsidian-border p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <CheckCircle2 className="w-5 h-5 text-cyber-green" />
                        <h4 className="text-sm font-bold text-obsidian-textBright">QA & Playwright Audit Summary</h4>
                      </div>
                      {projectStatus.latest_test_run ? (
                        <div className="space-y-2 text-xs">
                          <p>
                            <span className="text-obsidian-text">Kết quả:</span>
                            <span className={`ml-2 font-bold ${projectStatus.latest_test_run.passed ? 'text-cyber-green' : 'text-cyber-red'}`}>
                              {projectStatus.latest_test_run.passed ? 'PASSED' : 'FAILED'}
                            </span>
                          </p>
                          <p>
                            <span className="text-obsidian-text">Console Violations:</span>
                            <span className="text-obsidian-textBright ml-2 font-semibold">{projectStatus.latest_test_run.console_violations}</span>
                          </p>
                          <p>
                            <span className="text-obsidian-text">Lần quét cuối:</span>
                            <span className="text-obsidian-textBright ml-2">{new Date(projectStatus.latest_test_run.timestamp).toLocaleString()}</span>
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-obsidian-text py-4">Chưa có kết quả audit nào từ Playwright.</p>
                      )}
                    </div>
                    {projectStatus.latest_test_run && (
                      <a 
                        href={`/projects/${projectStatus.project.id}/assets/test_report.html`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="mt-4 flex items-center justify-center gap-2 bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-4 py-2 rounded-lg text-xs font-semibold transition-all w-fit cursor-pointer"
                      >
                        <Eye className="w-4 h-4 text-rosegold" />
                        <span>Xem Playwright Report HTML</span>
                      </a>
                    )}
                  </div>

                  {/* Security report summary */}
                  <div className="bg-obsidian-card/30 rounded-xl border border-obsidian-border p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <ShieldAlert className="w-5 h-5 text-rosegold" />
                        <h4 className="text-sm font-bold text-obsidian-textBright">SAST Security Vulnerabilities Summary</h4>
                      </div>
                      {projectStatus.latest_security_scan ? (
                        <div className="space-y-2 text-xs">
                          <p>
                            <span className="text-obsidian-text">Trạng thái an toàn:</span>
                            <span className={`ml-2 font-bold ${projectStatus.latest_security_scan.passed ? 'text-cyber-green' : 'text-cyber-red'}`}>
                              {projectStatus.latest_security_scan.passed ? 'SECURE' : 'VULNERABLE'}
                            </span>
                          </p>
                          <p>
                            <span className="text-obsidian-text">Vulnerabilities Found:</span>
                            <span className="text-obsidian-textBright ml-2 font-semibold text-rosegold">{projectStatus.latest_security_scan.vulnerabilities_found}</span>
                          </p>
                          <p>
                            <span className="text-obsidian-text">Lần quét cuối:</span>
                            <span className="text-obsidian-textBright ml-2">{new Date(projectStatus.latest_security_scan.timestamp).toLocaleString()}</span>
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-obsidian-text py-4">Chưa thực hiện rà quét bảo mật SAST.</p>
                      )}
                    </div>
                    {projectStatus.latest_security_scan && (
                      <a 
                        href={`/projects/${projectStatus.project.id}/security_report.md`} 
                        target="_blank" 
                        rel="noreferrer"
                        className="mt-4 flex items-center justify-center gap-2 bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-4 py-2 rounded-lg text-xs font-semibold transition-all w-fit cursor-pointer"
                      >
                        <Download className="w-4 h-4 text-cyber-cyan" />
                        <span>Xem Security Report MD</span>
                      </a>
                    )}
                  </div>
                </div>

                {/* Expose link to actual preview */}
                {projectStatus.project.status === 'PASSED' && (
                  <div className="mt-6 p-4 bg-cyber-green/5 border border-cyber-green/20 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-cyber-green" />
                      <div>
                        <h4 className="text-xs font-bold text-obsidian-textBright">Mã nguồn được sinh hoàn chỉnh và vượt qua các bài kiểm thử!</h4>
                        <p className="text-[10px] text-obsidian-text mt-0.5">Ứng dụng đã sẵn sàng chạy và được đóng gói tĩnh.</p>
                      </div>
                    </div>
                    <a 
                      href={`/projects/${projectStatus.project.id}/index.html`} 
                      target="_blank" 
                      rel="noreferrer"
                      className="bg-cyber-green text-obsidian-bg font-bold px-4 py-2 rounded-lg text-xs uppercase hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
                    >
                      Mở ứng dụng Live Preview
                    </a>
                  </div>
                )}

              </div>
            )}

          </div>
        )}

        {/* VIEW 2: Agile Backlog */}
        {currentView === 'backlog' && (
          <div className="space-y-6">
            
            {/* Header controls for Backlog */}
            <div className="flex items-center justify-between flex-wrap gap-4 bg-obsidian-card/20 p-4 rounded-xl border border-obsidian-border">
              <div className="flex items-center gap-4">
                <h3 className="text-lg font-black text-obsidian-textBright">Product Backlog Management</h3>
                <span className="text-xs bg-rosegold-glow text-rosegold px-2.5 py-1 rounded-full border border-rosegold/20 font-semibold">
                  {stories.length} stories
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setShowAddStoryForm(!showAddStoryForm)}
                  className="flex items-center gap-1 bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  <Plus className="w-4 h-4 text-rosegold" />
                  <span>Viết Story mới</span>
                </button>
                <button 
                  onClick={handleGenerateStories}
                  disabled={isGeneratingStories || !selectedProjectId}
                  className="flex items-center gap-1.5 bg-rosegold hover:bg-rosegold-dark text-obsidian-bg px-4 py-2 rounded-lg text-xs font-bold transition-all disabled:bg-obsidian-hover disabled:text-obsidian-text cursor-pointer"
                >
                  {isGeneratingStories ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  <span>Generate Backlog (AI)</span>
                </button>
                <button 
                  onClick={handlePrioritizeBacklog}
                  disabled={isPrioritizing || stories.length === 0}
                  className="flex items-center gap-1.5 bg-cyber-cyan hover:bg-cyber-cyan/80 text-obsidian-bg px-4 py-2 rounded-lg text-xs font-bold transition-all disabled:bg-obsidian-hover disabled:text-obsidian-text cursor-pointer"
                >
                  {isPrioritizing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                  <span>Prioritize & Estimate (MoSCoW/Fibonacci)</span>
                </button>
              </div>
            </div>

            {/* Inline creation form */}
            {showAddStoryForm && (
              <form onSubmit={handleCreateStory} className="glass-panel p-6 rounded-xl border border-obsidian-border space-y-4">
                <h4 className="text-xs font-black text-obsidian-textBright uppercase tracking-wider mb-2">Tạo Story Thủ công</h4>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="md:col-span-3">
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Story Title</label>
                    <input 
                      type="text" 
                      required
                      value={newStoryTitle}
                      onChange={(e) => setNewStoryTitle(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. Đăng nhập tài khoản bằng email"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">As a (Vai trò)</label>
                    <input 
                      type="text" 
                      value={newStoryPersona}
                      onChange={(e) => setNewStoryPersona(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. Khách vãng lai"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">I want to (Hành động)</label>
                    <input 
                      type="text" 
                      value={newStoryWant}
                      onChange={(e) => setNewStoryWant(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. nhập email và mật khẩu của tôi"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">So that (Giá trị)</label>
                    <input 
                      type="text" 
                      value={newStoryBenefit}
                      onChange={(e) => setNewStoryBenefit(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. đăng nhập để truy cập tài khoản cá nhân"
                    />
                  </div>
                  <div className="md:col-span-3">
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Acceptance Criteria (Tiêu chí nghiệm thu - Xuống dòng cho mỗi tiêu chí)</label>
                    <textarea 
                      rows={3}
                      value={newStoryAC}
                      onChange={(e) => setNewStoryAC(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold resize-none"
                      placeholder="Given email hợp lệ và đúng mật khẩu&#10;When bấm nút đăng nhập&#10;Then hệ thống đăng nhập thành công và chuyển về trang dashboard."
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button 
                    type="submit" 
                    className="bg-rosegold hover:bg-rosegold-dark text-obsidian-bg font-bold px-4 py-2 rounded-lg text-xs uppercase cursor-pointer"
                  >
                    Lưu Story
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setShowAddStoryForm(false)}
                    className="bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Hủy bỏ
                  </button>
                </div>
              </form>
            )}

            {/* Backlog Stories Grid/List */}
            <div className="space-y-3">
              {stories.length === 0 ? (
                <div className="text-center py-16 bg-obsidian-card/10 border border-obsidian-border border-dashed rounded-xl">
                  <Info className="w-8 h-8 text-rosegold mx-auto mb-2 opacity-50" />
                  <p className="text-sm text-obsidian-text">Dự án này chưa có stories nào. Hãy nhấn nút <strong>Generate Backlog (AI)</strong> để tự động phân tích requirements.</p>
                </div>
              ) : (
                stories.map(story => (
                  <div key={story.id} className="glass-panel p-5 rounded-xl border border-obsidian-border flex flex-col md:flex-row justify-between gap-6 relative group">
                    <div className="flex-grow space-y-2.5">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {/* MoSCoW Priority Badge */}
                        <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded ${
                          story.priority === 'Must' ? 'bg-cyber-red/10 text-cyber-red border border-cyber-red/20' :
                          story.priority === 'Should' ? 'bg-rosegold/10 text-rosegold border border-rosegold/20' :
                          story.priority === 'Could' ? 'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20' :
                          'bg-obsidian-hover text-obsidian-text border border-obsidian-border'
                        }`}>
                          {story.priority || 'Should'}
                        </span>
                        {/* Story Points badge */}
                        <span className="text-[9px] font-bold uppercase bg-obsidian-hover text-obsidian-textBright border border-obsidian-border px-2 py-0.5 rounded">
                          {story.story_points ? `${story.story_points} Points` : 'No points'}
                        </span>
                        {/* Status badge */}
                        <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded border ${
                          story.status === 'done' ? 'bg-cyber-green/10 text-cyber-green border-cyber-green/20' :
                          story.status === 'in_progress' ? 'bg-cyber-cyan/10 text-cyber-cyan border-cyber-cyan/20 animate-pulse' :
                          story.status === 'todo' ? 'bg-rosegold/10 text-rosegold border-rosegold/20' :
                          'bg-obsidian-bg text-obsidian-text border-obsidian-border'
                        }`}>
                          {story.status}
                        </span>
                      </div>

                      <h4 className="text-sm font-bold text-obsidian-textBright">{story.title}</h4>
                      <p className="text-xs text-obsidian-textBright leading-relaxed bg-obsidian-bg/30 p-2.5 rounded border border-obsidian-border/20">
                        {story.description}
                      </p>

                      {story.acceptance_criteria && (
                        <div className="text-[10px] text-obsidian-text bg-obsidian-bg/10 p-2 rounded">
                          <p className="font-bold text-obsidian-textBright mb-1">Tiêu chí nghiệm thu (Acceptance Criteria):</p>
                          <ul className="list-disc pl-4 space-y-1">
                            {story.acceptance_criteria.split('\n').map((ac, idx) => ac.trim() && <li key={idx}>{ac}</li>)}
                          </ul>
                        </div>
                      )}

                      {story.complexity_rationale && (
                        <div className="text-[9px] text-rosegold/80 flex items-start gap-1">
                          <Info className="w-3.5 h-3.5 flex-shrink-0" />
                          <span>Complexity: {story.complexity_rationale}</span>
                        </div>
                      )}
                    </div>

                    {/* Actions column on story */}
                    <div className="flex flex-row md:flex-col justify-end items-end gap-2.5 flex-shrink-0">
                      {/* Sprint selector */}
                      {sprints.length > 0 && story.sprint_id === null && (
                        <div className="relative">
                          <select 
                            onChange={(e) => {
                              const sId = parseInt(e.target.value);
                              if (sId) handleSprintAddStory(sId, story.id);
                            }}
                            className="bg-obsidian-bg border border-obsidian-border rounded px-2 py-1 text-[10px] text-obsidian-textBright focus:outline-none focus:border-rosegold cursor-pointer"
                          >
                            <option value="">+ Đưa vào Sprint</option>
                            {sprints.map(s => (
                              <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                          </select>
                        </div>
                      )}
                      
                      <div className="flex items-center gap-1.5">
                        <button 
                          onClick={() => handleBreakdownTasks(story.id)}
                          disabled={loadingTasksStoryId === story.id}
                          className="flex items-center gap-1 bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-2.5 py-1.5 rounded text-[10px] font-bold transition-all disabled:opacity-50 cursor-pointer"
                          title="Phân rã stories thành các dev tasks kỹ thuật"
                        >
                          {loadingTasksStoryId === story.id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <CheckSquare className="w-3.5 h-3.5 text-rosegold" />}
                          <span>{storyTasks[story.id]?.length > 0 ? "Re-breakdown" : "Breakdown Tasks"}</span>
                        </button>
                        <button 
                          onClick={() => openEditModal(story)}
                          className="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-obsidian-text hover:text-obsidian-textBright transition-all cursor-pointer"
                          title="Sửa Story"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button 
                          onClick={() => handleDeleteStory(story.id)}
                          className="p-1.5 rounded bg-obsidian-hover border border-obsidian-border text-obsidian-text hover:text-cyber-red transition-all cursor-pointer"
                          title="Xóa Story"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Manual status dropdown */}
                      <div className="relative mt-1">
                        <select 
                          value={story.status}
                          onChange={(e) => handleUpdateStoryStatus(story.id, e.target.value)}
                          className="bg-obsidian-bg border border-obsidian-border rounded px-2 py-1 text-[10px] text-obsidian-textBright focus:outline-none cursor-pointer"
                        >
                          <option value="backlog">Backlog</option>
                          <option value="todo">Todo</option>
                          <option value="in_progress">In Progress</option>
                          <option value="done">Done</option>
                        </select>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Story Edit Modal */}
            {editingStory && (
              <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="glass-panel w-full max-w-xl p-6 rounded-2xl border border-obsidian-border space-y-4 shadow-2xl relative">
                  <div className="flex items-center justify-between border-b border-obsidian-border/50 pb-3 mb-2">
                    <h3 className="text-sm font-black text-obsidian-textBright uppercase tracking-wider">Chỉnh sửa User Story #{editingStory.id}</h3>
                    <button 
                      onClick={() => setEditingStory(null)} 
                      className="text-obsidian-text hover:text-obsidian-textBright text-lg font-bold"
                    >
                      &times;
                    </button>
                  </div>
                  
                  <div className="space-y-4">
                    <div>
                      <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Title</label>
                      <input 
                        type="text" 
                        value={editStoryTitle}
                        onChange={(e) => setEditStoryTitle(e.target.value)}
                        className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Mô tả chi tiết</label>
                      <textarea 
                        rows={3}
                        value={editStoryDesc}
                        onChange={(e) => setEditStoryDesc(e.target.value)}
                        className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold resize-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Tiêu chí nghiệm thu (Acceptance Criteria)</label>
                      <textarea 
                        rows={3}
                        value={editStoryAC}
                        onChange={(e) => setEditStoryAC(e.target.value)}
                        className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold resize-none"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Độ ưu tiên MoSCoW</label>
                        <select 
                          value={editStoryPriority}
                          onChange={(e) => setEditStoryPriority(e.target.value)}
                          className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                        >
                          <option value="Must">Must</option>
                          <option value="Should">Should</option>
                          <option value="Could">Could</option>
                          <option value="Won't">Won't</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Effort Story Points</label>
                        <input 
                          type="number" 
                          value={editStoryPoints}
                          onChange={(e) => setEditStoryPoints(parseInt(e.target.value))}
                          className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Trạng thái</label>
                        <select 
                          value={editStoryStatus}
                          onChange={(e) => setEditStoryStatus(e.target.value)}
                          className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none"
                        >
                          <option value="backlog">Backlog</option>
                          <option value="todo">Todo</option>
                          <option value="in_progress">In Progress</option>
                          <option value="done">Done</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2 justify-end pt-4 border-t border-obsidian-border/50">
                    <button 
                      onClick={handleSaveStoryEdit}
                      className="bg-rosegold hover:bg-rosegold-dark text-obsidian-bg font-bold px-4 py-2 rounded-lg text-xs uppercase cursor-pointer"
                    >
                      Lưu thay đổi
                    </button>
                    <button 
                      onClick={() => setEditingStory(null)}
                      className="bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer"
                    >
                      Hủy bỏ
                    </button>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}

        {/* VIEW 3: Sprint Board */}
        {currentView === 'sprint' && (
          <div className="space-y-6">
            
            {/* Header controls for Sprint */}
            <div className="flex items-center justify-between flex-wrap gap-4 bg-obsidian-card/20 p-4 rounded-xl border border-obsidian-border">
              <div className="flex items-center gap-4">
                <h3 className="text-lg font-black text-obsidian-textBright">Agile Sprint Management</h3>
                <span className="text-xs bg-cyber-cyanGlow text-cyber-cyan px-2.5 py-1 rounded-full border border-cyber-cyan/20 font-semibold">
                  {sprints.length} sprints
                </span>
              </div>
              
              <button 
                onClick={() => setShowAddSprintForm(!showAddSprintForm)}
                className="flex items-center gap-1 bg-rosegold hover:bg-rosegold-dark text-obsidian-bg px-4 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                <Plus className="w-4.5 h-4.5" />
                <span>Tạo Sprint mới</span>
              </button>
            </div>

            {/* Inline sprint creation form */}
            {showAddSprintForm && (
              <form onSubmit={handleCreateSprint} className="glass-panel p-6 rounded-xl border border-obsidian-border space-y-4">
                <h4 className="text-xs font-black text-obsidian-textBright uppercase tracking-wider mb-2">Tạo Sprint mới</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Tên Sprint</label>
                    <input 
                      type="text" 
                      required
                      value={newSprintName}
                      onChange={(e) => setNewSprintName(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. Sprint 1 - MVP Login"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-obsidian-text mb-1">Mục tiêu Sprint (Sprint Goal)</label>
                    <input 
                      type="text" 
                      value={newSprintGoal}
                      onChange={(e) => setNewSprintGoal(e.target.value)}
                      className="w-full bg-obsidian-bg border border-obsidian-border rounded-lg px-3 py-2 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold"
                      placeholder="e.g. Hoàn thành toàn bộ chức năng đăng ký và xác thực người dùng"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button 
                    type="submit" 
                    className="bg-cyber-cyan text-obsidian-bg font-bold px-4 py-2 rounded-lg text-xs uppercase cursor-pointer"
                  >
                    Tạo Sprint
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setShowAddSprintForm(false)}
                    className="bg-obsidian-hover hover:bg-obsidian-hover/80 text-obsidian-textBright border border-obsidian-border px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Hủy bỏ
                  </button>
                </div>
              </form>
            )}

            {/* Split layout: Burndown chart & Active Sprint columns */}
            {sprints.length === 0 ? (
              <div className="text-center py-16 bg-obsidian-card/10 border border-obsidian-border border-dashed rounded-xl">
                <Calendar className="w-8 h-8 text-rosegold mx-auto mb-2 opacity-50" />
                <p className="text-sm text-obsidian-text">Chưa có sprint nào được tạo. Hãy tạo một sprint mới và gán stories từ backlog.</p>
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* Sprint Burndown chart (Custom SVG representation) */}
                <div className="glass-panel p-6 rounded-2xl border border-obsidian-border">
                  <div className="flex justify-between items-center mb-4">
                    <div>
                      <span className="text-[10px] text-cyber-cyan uppercase tracking-wider font-bold">Biểu đồ tiến độ</span>
                      <h3 className="text-sm font-black text-obsidian-textBright mt-0.5">Sprint Burndown Chart (Remaining Story Points)</h3>
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-0.5 bg-rosegold"></div>
                        <span className="text-obsidian-text">Lý tưởng</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-3 h-0.5 bg-cyber-cyan"></div>
                        <span className="text-obsidian-text">Thực tế</span>
                      </div>
                    </div>
                  </div>

                  {/* Draw simple burndown chart */}
                  <div className="h-[180px] w-full flex items-end">
                    <svg className="w-full h-full" viewBox="0 0 600 150">
                      {/* Grid lines */}
                      <line x1="40" y1="10" x2="580" y2="10" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                      <line x1="40" y1="45" x2="580" y2="45" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                      <line x1="40" y1="80" x2="580" y2="80" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                      <line x1="40" y1="115" x2="580" y2="115" stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
                      <line x1="40" y1="140" x2="580" y2="140" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />

                      {/* Ideal Line (Diagonal) */}
                      <line x1="40" y1="10" x2="580" y2="140" stroke="#e0a96d" strokeDasharray="4" strokeWidth="2" />
                      
                      {/* Actual Line (Simulated based on stories progress) */}
                      {/* Start points: sum of all story points in active sprint */}
                      {/* Day 0: 100%, Day 3: 80%, Day 6: 40%, Day 10: 0% */}
                      <path 
                        d="M 40 10 L 150 20 L 280 40 L 410 80 L 520 120 L 580 140" 
                        fill="none" 
                        stroke="#00f2fe" 
                        strokeWidth="3" 
                      />

                      {/* Data Dots */}
                      <circle cx="40" cy="10" r="4" fill="#00f2fe" />
                      <circle cx="150" cy="20" r="4" fill="#00f2fe" />
                      <circle cx="280" cy="40" r="4" fill="#00f2fe" />
                      <circle cx="410" cy="80" r="4" fill="#00f2fe" />
                      <circle cx="580" cy="140" r="4" fill="#00f2fe" />

                      {/* Axes */}
                      <text x="35" y="15" fill="#94a3b8" fontSize="8" textAnchor="end">30 SP</text>
                      <text x="35" y="80" fill="#94a3b8" fontSize="8" textAnchor="end">15 SP</text>
                      <text x="35" y="140" fill="#94a3b8" fontSize="8" textAnchor="end">0 SP</text>
                      
                      <text x="40" y="150" fill="#94a3b8" fontSize="8" textAnchor="middle">Day 0</text>
                      <text x="280" y="150" fill="#94a3b8" fontSize="8" textAnchor="middle">Day 5</text>
                      <text x="580" y="150" fill="#94a3b8" fontSize="8" textAnchor="middle">Day 10</text>
                    </svg>
                  </div>
                </div>

                {/* Sprints listing and boards */}
                {sprints.map(sprint => {
                  const sprintStories = stories.filter(st => st.sprint_id === sprint.id);
                  
                  return (
                    <div key={sprint.id} className="glass-panel p-6 rounded-2xl border border-obsidian-border space-y-4">
                      <div className="flex items-center justify-between border-b border-obsidian-border/50 pb-3 mb-2 flex-wrap gap-2">
                        <div>
                          <span className="text-[10px] text-rosegold uppercase tracking-wider font-bold">Active Sprint</span>
                          <h4 className="text-base font-bold text-obsidian-textBright">{sprint.name}</h4>
                          {sprint.goal && (
                            <p className="text-xs text-obsidian-text mt-0.5 font-medium">Goal: {sprint.goal}</p>
                          )}
                        </div>
                        <span className="px-2.5 py-0.5 rounded bg-cyber-green/10 text-cyber-green border border-cyber-green/20 text-[10px] uppercase font-bold">
                          {sprint.status}
                        </span>
                      </div>

                      {/* Kanban Columns */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        
                        {/* COLUMN 1: TODO */}
                        <div className="bg-obsidian-bg/40 rounded-xl border border-obsidian-border p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-obsidian-border/30 pb-2">
                            <span className="text-xs font-bold text-obsidian-textBright uppercase">To Do</span>
                            <span className="bg-obsidian-hover text-obsidian-text px-2 py-0.5 rounded-full text-[10px] font-bold">
                              {sprintStories.filter(st => st.status === 'todo').length}
                            </span>
                          </div>
                          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                            {sprintStories.filter(st => st.status === 'todo').map(story => (
                              <KanbanCard 
                                key={story.id} 
                                story={story} 
                                onMoveStatus={handleUpdateStoryStatus}
                                devTasks={storyTasks[story.id] || []}
                                onToggleTask={handleToggleTask}
                                onFetchTasks={fetchDevTasks}
                              />
                            ))}
                          </div>
                        </div>

                        {/* COLUMN 2: IN PROGRESS */}
                        <div className="bg-obsidian-bg/40 rounded-xl border border-obsidian-border p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-obsidian-border/30 pb-2">
                            <span className="text-xs font-bold text-cyber-cyan uppercase">In Progress</span>
                            <span className="bg-obsidian-hover text-cyber-cyan px-2 py-0.5 rounded-full text-[10px] font-bold">
                              {sprintStories.filter(st => st.status === 'in_progress').length}
                            </span>
                          </div>
                          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                            {sprintStories.filter(st => st.status === 'in_progress').map(story => (
                              <KanbanCard 
                                key={story.id} 
                                story={story} 
                                onMoveStatus={handleUpdateStoryStatus}
                                devTasks={storyTasks[story.id] || []}
                                onToggleTask={handleToggleTask}
                                onFetchTasks={fetchDevTasks}
                              />
                            ))}
                          </div>
                        </div>

                        {/* COLUMN 3: DONE */}
                        <div className="bg-obsidian-bg/40 rounded-xl border border-obsidian-border p-4 space-y-3">
                          <div className="flex items-center justify-between border-b border-obsidian-border/30 pb-2">
                            <span className="text-xs font-bold text-cyber-green uppercase">Done</span>
                            <span className="bg-obsidian-hover text-cyber-green px-2 py-0.5 rounded-full text-[10px] font-bold">
                              {sprintStories.filter(st => st.status === 'done').length}
                            </span>
                          </div>
                          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
                            {sprintStories.filter(st => st.status === 'done').map(story => (
                              <KanbanCard 
                                key={story.id} 
                                story={story} 
                                onMoveStatus={handleUpdateStoryStatus}
                                devTasks={storyTasks[story.id] || []}
                                onToggleTask={handleToggleTask}
                                onFetchTasks={fetchDevTasks}
                              />
                            ))}
                          </div>
                        </div>

                      </div>
                    </div>
                  );
                })}
              </div>
            )}

          </div>
        )}

        {/* VIEW 4: PO Chat Assistant */}
        {currentView === 'chat' && (
          <div className="glass-panel rounded-2xl border border-obsidian-border h-[calc(100vh-180px)] flex flex-col overflow-hidden">
            {/* Chat header */}
            <div className="border-b border-obsidian-border/50 px-6 py-4 flex items-center justify-between bg-obsidian-card/30 flex-shrink-0">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-cyber-green animate-pulse"></div>
                <h3 className="text-sm font-bold text-obsidian-textBright">Product Owner Assistant Agent</h3>
              </div>
              <button 
                onClick={() => setChatMessages([
                  { role: 'assistant', content: 'Chào bạn! Tôi là Product Owner Agent. Hãy hỏi tôi về yêu cầu dự án, cách viết user story, phân chia sprint hoặc thiết lập các task phát triển nhé!' }
                ])}
                className="text-xs text-rosegold hover:underline flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Xóa lịch sử chat</span>
              </button>
            </div>

            {/* Scrolling message log */}
            <div className="flex-grow p-6 overflow-y-auto space-y-4">
              {chatMessages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
                >
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border text-xs font-bold ${
                    msg.role === 'user' ? 'bg-rosegold text-obsidian-bg border-rosegold/30' : 'bg-obsidian-card text-cyber-cyan border-obsidian-border'
                  }`}>
                    {msg.role === 'user' ? 'ME' : 'PO'}
                  </div>

                  {/* Body speech bubble */}
                  <div className={`rounded-xl px-4 py-3 text-xs leading-relaxed ${
                    msg.role === 'user' ? 'bg-rosegold-glow text-obsidian-textBright border border-rosegold/20 rounded-tr-none' : 'bg-obsidian-card/60 text-obsidian-textBright border border-obsidian-border rounded-tl-none'
                  }`}>
                    {msg.content.split('\n').map((line, lIdx) => (
                      <p key={lIdx} className={lIdx > 0 ? 'mt-1.5' : ''}>{line}</p>
                    ))}
                  </div>
                </div>
              ))}
              {isChatLoading && (
                <div className="flex gap-3 max-w-[85%]">
                  <div className="w-8 h-8 rounded-full bg-obsidian-card text-cyber-cyan border border-obsidian-border flex items-center justify-center text-xs font-bold">
                    PO
                  </div>
                  <div className="bg-obsidian-card/60 text-obsidian-text border border-obsidian-border rounded-xl rounded-tl-none px-4 py-3 text-xs flex items-center gap-1.5">
                    <span className="w-2 h-2 bg-rosegold rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-2 h-2 bg-rosegold rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-2 h-2 bg-rosegold rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef}></div>
            </div>

            {/* Input form */}
            <form onSubmit={handleSendChatMessage} className="border-t border-obsidian-border/50 p-4 bg-obsidian-card/10 flex gap-3 flex-shrink-0">
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                disabled={isChatLoading}
                className="flex-grow bg-obsidian-bg border border-obsidian-border rounded-xl px-4 py-3 text-xs text-obsidian-textBright focus:outline-none focus:border-rosegold transition-colors disabled:opacity-50 placeholder-obsidian-text/40"
                placeholder="Hỏi trợ lý PO (Ví dụ: 'Viết thêm user story cho tính năng thanh toán Momo')..."
              />
              <button 
                type="submit"
                disabled={isChatLoading || !chatInput.trim()}
                className="bg-rosegold hover:bg-rosegold-dark disabled:bg-obsidian-hover disabled:text-obsidian-text text-obsidian-bg p-3 rounded-xl transition-all shadow-glow-rose hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
              >
                <Send className="w-4.5 h-4.5" />
              </button>
            </form>
          </div>
        )}

      </main>
    </div>
  );
}

// Sub-component: Kanban story card
interface KanbanCardProps {
  story: UserStory;
  onMoveStatus: (storyId: number, status: string) => void;
  devTasks: DevTask[];
  onToggleTask: (taskId: number, currentStatus: string, storyId: number) => void;
  onFetchTasks: (storyId: number) => void;
}

function KanbanCard({ story, onMoveStatus, devTasks, onToggleTask, onFetchTasks }: KanbanCardProps) {
  const [collapsed, setCollapsed] = useState(true);

  // Fetch tasks on initial expand
  const handleCollapseToggle = () => {
    if (collapsed && devTasks.length === 0) {
      onFetchTasks(story.id);
    }
    setCollapsed(!collapsed);
  };

  const doneTasks = devTasks.filter(t => t.status === 'done').length;
  const progressPercent = devTasks.length > 0 ? Math.round((doneTasks / devTasks.length) * 100) : 0;

  return (
    <div className="bg-obsidian-card border border-obsidian-border/80 rounded-xl p-3.5 space-y-3 shadow hover:border-obsidian-text/20 transition-all">
      <div className="space-y-1">
        <div className="flex justify-between items-start gap-2">
          <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded ${
            story.priority === 'Must' ? 'bg-cyber-red/10 text-cyber-red border border-cyber-red/15' :
            story.priority === 'Should' ? 'bg-rosegold/10 text-rosegold border border-rosegold/15' :
            'bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/15'
          }`}>
            {story.priority || 'Should'}
          </span>
          
          {/* Quick status moves */}
          <div className="flex gap-0.5">
            {story.status !== 'todo' && (
              <button 
                onClick={() => onMoveStatus(story.id, 'todo')}
                className="text-[8px] text-obsidian-text hover:text-rosegold px-1 bg-obsidian-bg rounded border border-obsidian-border/50 cursor-pointer"
                title="Move to Todo"
              >
                Todo
              </button>
            )}
            {story.status !== 'in_progress' && (
              <button 
                onClick={() => onMoveStatus(story.id, 'in_progress')}
                className="text-[8px] text-obsidian-text hover:text-cyber-cyan px-1 bg-obsidian-bg rounded border border-obsidian-border/50 cursor-pointer"
                title="Move to In Progress"
              >
                IP
              </button>
            )}
            {story.status !== 'done' && (
              <button 
                onClick={() => onMoveStatus(story.id, 'done')}
                className="text-[8px] text-obsidian-text hover:text-cyber-green px-1 bg-obsidian-bg rounded border border-obsidian-border/50 cursor-pointer"
                title="Move to Done"
              >
                Done
              </button>
            )}
          </div>
        </div>
        <h5 className="text-xs font-bold text-obsidian-textBright leading-tight">{story.title}</h5>
      </div>

      <p className="text-[10px] text-obsidian-text line-clamp-2 leading-relaxed bg-obsidian-bg/20 p-2 rounded">
        {story.description}
      </p>

      {/* Progress tracker */}
      {devTasks.length > 0 && (
        <div className="space-y-1">
          <div className="flex justify-between items-center text-[9px]">
            <span className="text-obsidian-text">Tasks: {doneTasks}/{devTasks.length}</span>
            <span className="text-obsidian-textBright font-semibold">{progressPercent}%</span>
          </div>
          <div className="w-full bg-obsidian-bg rounded-full h-1 overflow-hidden border border-obsidian-border/20">
            <div 
              className="bg-cyber-cyan h-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Collapse button for DevTasks list */}
      <button 
        onClick={handleCollapseToggle}
        className="flex items-center gap-0.5 text-[9px] text-rosegold hover:underline font-semibold cursor-pointer"
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        <span>{collapsed ? "Xem Dev Tasks" : "Ẩn Dev Tasks"}</span>
      </button>

      {/* Dev tasks checklists */}
      {!collapsed && (
        <div className="pt-2 border-t border-obsidian-border/30 space-y-1.5 max-h-[160px] overflow-y-auto">
          {devTasks.length === 0 ? (
            <p className="text-[9px] text-obsidian-text italic">Không có tasks. Vui lòng bấm "Breakdown Tasks" tại màn hình Backlog.</p>
          ) : (
            devTasks.map(task => (
              <div 
                key={task.id} 
                onClick={() => onToggleTask(task.id, task.status, story.id)}
                className="flex items-start gap-1.5 text-[9px] text-obsidian-textBright hover:text-rosegold cursor-pointer select-none bg-obsidian-bg/40 p-1.5 rounded border border-obsidian-border/20"
              >
                {task.status === 'done' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-cyber-green flex-shrink-0 mt-0.5" />
                ) : (
                  <div className="w-3.5 h-3.5 border border-obsidian-text rounded flex-shrink-0 mt-0.5"></div>
                )}
                <div className="leading-tight">
                  <span className="font-bold text-[8px] uppercase tracking-wider text-rosegold mr-1">[{task.task_type}]</span>
                  <span className={task.status === 'done' ? 'line-through text-obsidian-text' : ''}>
                    {task.task_name}
                  </span>
                  {task.description && (
                    <p className="text-[8px] text-obsidian-text mt-0.5 leading-normal">{task.description}</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
