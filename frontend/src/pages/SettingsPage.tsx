import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { Navbar } from '../components/Navbar';
import { KeyRound, RefreshCw, GitFork, ExternalLink } from 'lucide-react';

interface Provider {
  id: number;
  name: string;
  provider_type: string;
  is_valid: boolean;
}

interface Repository {
  id: number;
  full_name: string;
  default_branch: string;
  web_url: string;
  is_monitored: boolean;
}

export const SettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [tokenInput, setTokenInput] = useState('');
  const [nameInput, setNameInput] = useState('GitHub Work');
  const [loading, setLoading] = useState(false);
  const [syncingId, setSyncingId] = useState<number | null>(null);

  const loadData = async () => {
    try {
      const [provRes, repoRes] = await Promise.all([
        api.get('/providers'),
        api.get('/repositories')
      ]);
      setProviders(provRes.data);
      setRepositories(repoRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/providers', {
        name: nameInput,
        token: tokenInput,
        provider_type: 'GITHUB'
      });
      setTokenInput('');
      await loadData();
      alert('GitHub токен успешно подключен и зашифрован');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Ошибка при проверке токена');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncRepos = async (providerId: number) => {
    setSyncingId(providerId);
    try {
      await api.post(`/providers/${providerId}/sync`);
      await loadData();
    } catch (err) {
      alert('Ошибка при импорте репозиториев');
    } finally {
      setSyncingId(null);
    }
  };

  const handleToggleRepo = async (repoId: number, currentStatus: boolean) => {
    try {
      await api.patch(`/repositories/${repoId}`, {
        is_monitored: !currentStatus
      });
      setRepositories(repos =>
        repos.map(r => (r.id === repoId ? { ...r, is_monitored: !currentStatus } : r))
      );
    } catch (err) {
      alert('Не удалось изменить статус отслеживания');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 pb-12">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 mt-8 space-y-8">
        {/* Форма добавления токена */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
            <KeyRound size={20} className="text-blue-500" /> Подключение GitHub PAT
          </h2>
          <p className="text-slate-400 text-sm mb-6">
            Введите персональный токен доступа (Personal Access Token с правами <code>repo</code> и <code>workflow</code>).
            Токен шифруется алгоритмом Fernet (AES-128) перед записью в базу данных.
          </p>

          <form onSubmit={handleAddProvider} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs uppercase text-slate-400 mb-1">Название подключения</label>
              <input
                type="text"
                required
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs uppercase text-slate-400 mb-1">Токен (PAT)</label>
              <input
                type="password"
                required
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg transition disabled:opacity-50"
              >
                {loading ? 'Проверка...' : 'Сохранить провайдер'}
              </button>
            </div>
          </form>
        </div>

        {/* Список подключений */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white mb-4">Активные интеграции</h2>
          {providers.length === 0 ? (
            <p className="text-slate-500 text-sm">Подключений пока нет.</p>
          ) : (
            <div className="space-y-3">
              {providers.map((p) => (
                <div key={p.id} className="flex items-center justify-between p-4 bg-slate-800/40 border border-slate-800 rounded-lg">
                  <div>
                    <span className="font-semibold text-white">{p.name}</span>
                    <span className="ml-3 text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded">
                      {p.provider_type}
                    </span>
                  </div>
                  <button
                    onClick={() => handleSyncRepos(p.id)}
                    disabled={syncingId === p.id}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-blue-400 border border-slate-700 rounded-lg text-xs font-medium transition disabled:opacity-50"
                  >
                    <RefreshCw size={14} className={syncingId === p.id ? 'animate-spin' : ''} />
                    Импортировать репозитории
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Отслеживаемые репозитории */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <GitFork size={20} className="text-blue-500" /> Выбор отслеживаемых проектов
          </h2>
          {repositories.length === 0 ? (
            <p className="text-slate-500 text-sm">Репозитории еще не импортированы. Нажмите «Импортировать репозитории» выше.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {repositories.map((r) => (
                <div key={r.id} className="flex items-center justify-between p-3.5 bg-slate-800/30 border border-slate-800 rounded-lg">
                  <div className="truncate mr-3">
                    <a
                      href={r.web_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-white hover:text-blue-400 font-medium text-sm flex items-center gap-1 transition"
                    >
                      {r.full_name} <ExternalLink size={12} className="text-slate-500" />
                    </a>
                    <span className="text-xs text-slate-500 font-mono">Ветка: {r.default_branch}</span>
                  </div>
                  <button
                    onClick={() => handleToggleRepo(r.id, r.is_monitored)}
                    className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                      r.is_monitored
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 hover:bg-blue-600/30'
                        : 'bg-slate-800 text-slate-500 border border-slate-700 hover:bg-slate-700'
                    }`}
                  >
                    {r.is_monitored ? 'Отслеживается' : 'Отключен'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};