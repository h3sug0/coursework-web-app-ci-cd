import React, { useEffect, useState } from 'react';
import api from '../services/api';
import { Navbar } from '../components/Navbar';
import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  RotateCw, 
  RefreshCw, 
  GitBranch, 
  GitCommit, 
  PlayCircle 
} from 'lucide-react';

interface Pipeline {
  id: number;
  repo_name: string;
  branch: string;
  commit_sha: string;
  commit_message: string | null;
  author_name: string | null;
  status: 'SUCCESS' | 'FAILED' | 'RUNNING' | 'QUEUED' | 'CANCELED';
  duration_sec: number;
  started_at: string | null;
}

interface Metrics {
  total_runs: number;
  success_rate: number;
  running_count: number;
  failed_count: number;
}

export const DashboardPage: React.FC = () => {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [syncing, setSyncing] = useState<boolean>(false);
  const [rerunningId, setRerunningId] = useState<number | null>(null);

  const fetchData = async () => {
    try {
      const [pipeRes, metRes] = await Promise.all([
        api.get('/pipelines', { params: { status: statusFilter || undefined } }),
        api.get('/metrics/summary')
      ]);
      setPipelines(pipeRes.data);
      setMetrics(metRes.data);
    } catch (err) {
      console.error('Ошибка загрузки данных:', err);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post('/pipelines/sync');
      await fetchData();
    } catch (err) {
      alert('Ошибка при синхронизации с GitHub');
    } finally {
      setSyncing(false);
    }
  };

  const handleRerun = async (id: number) => {
    setRerunningId(id);
    try {
      await api.post(`/pipelines/${id}/rerun`);
      await fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Не удалось перезапустить сборку');
    } finally {
      setRerunningId(null);
    }
  };

  const getStatusBadge = (status: Pipeline['status']) => {
    switch (status) {
      case 'SUCCESS':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-semibold">
            <CheckCircle2 size={14} /> Успешно
          </span>
        );
      case 'FAILED':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-semibold">
            <XCircle size={14} /> Ошибка
          </span>
        );
      case 'RUNNING':
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-semibold animate-pulse">
            <RotateCw size={14} className="animate-spin" /> В процессе
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-full text-xs font-semibold">
            <Clock size={14} /> {status}
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 pb-12">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 mt-8">
        {/* KPI Карточки */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-slate-400 text-sm">Всего сборок</p>
            <p className="text-3xl font-bold text-white mt-1">{metrics?.total_runs || 0}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-slate-400 text-sm">Успешность (Success Rate)</p>
            <p className="text-3xl font-bold text-emerald-400 mt-1">{metrics?.success_rate || 0}%</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-slate-400 text-sm">В процессе</p>
            <p className="text-3xl font-bold text-blue-400 mt-1">{metrics?.running_count || 0}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-slate-400 text-sm">Сбоев</p>
            <p className="text-3xl font-bold text-red-400 mt-1">{metrics?.failed_count || 0}</p>
          </div>
        </div>

        {/* Панель управления и фильтров */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-300 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
            >
              <option value="">Все статусы</option>
              <option value="SUCCESS">Успешные</option>
              <option value="FAILED">С ошибкой</option>
              <option value="RUNNING">В процессе</option>
            </select>
          </div>

          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Синхронизация...' : 'Синхронизировать пайплайны'}
          </button>
        </div>

        {/* Таблица пайплайнов */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-800/60 text-slate-400 uppercase text-xs">
                <tr>
                  <th className="py-3 px-4">Репозиторий</th>
                  <th className="py-3 px-4">Ветка и коммит</th>
                  <th className="py-3 px-4">Длительность</th>
                  <th className="py-3 px-4">Статус</th>
                  <th className="py-3 px-4 text-right">Действие</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {pipelines.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      Сборки не найдены. Нажмите «Синхронизировать пайплайны» или проверьте настройки репозиториев.
                    </td>
                  </tr>
                ) : (
                  pipelines.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-4 px-4 font-semibold text-white">
                        {p.repo_name}
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-1.5 text-blue-400 font-mono text-xs">
                          <GitBranch size={13} /> {p.branch}
                        </div>
                        <div className="flex items-center gap-1 text-slate-400 text-xs mt-1 truncate max-w-xs">
                          <GitCommit size={13} /> <span className="font-mono">{p.commit_sha}</span>: {p.commit_message || 'Без описания'}
                        </div>
                      </td>
                      <td className="py-4 px-4 text-slate-400">
                        {p.duration_sec > 0 ? `${Math.floor(p.duration_sec / 60)}м ${p.duration_sec % 60}с` : '—'}
                      </td>
                      <td className="py-4 px-4">
                        {getStatusBadge(p.status)}
                      </td>
                      <td className="py-4 px-4 text-right">
                        <button
                          onClick={() => handleRerun(p.id)}
                          disabled={rerunningId === p.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
                        >
                          <PlayCircle size={14} className={rerunningId === p.id ? 'animate-spin' : ''} />
                          Re-run
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};