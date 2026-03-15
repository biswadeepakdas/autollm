"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useAuth } from "./AuthContext";
import { projects as projectsApi } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

interface ProjectState {
  projects: Project[];
  current: Project | null;
  loading: boolean;
  setCurrent: (project: Project) => void;
  reload: () => Promise<void>;
  createProject: (name: string) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
}

const ProjectContext = createContext<ProjectState | undefined>(undefined);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [current, setCurrent] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (!user) {
      setProjects([]);
      setCurrent(null);
      return;
    }
    setLoading(true);
    try {
      const list = await projectsApi.list();
      setProjects(list);
      if (list.length > 0 && !current) {
        setCurrent(list[0]);
      } else if (list.length === 0) {
        setCurrent(null);
      }
    } catch {
      // silently fail — user might not have projects yet
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    reload();
  }, [reload]);

  const createProject = async (name: string): Promise<Project> => {
    const proj = await projectsApi.create(name);
    await reload();
    setCurrent(proj);
    return proj;
  };

  const deleteProject = async (id: string) => {
    await projectsApi.delete(id);
    await reload();
  };

  return (
    <ProjectContext.Provider value={{ projects, current, loading, setCurrent, reload, createProject, deleteProject }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within ProjectProvider");
  return ctx;
}
