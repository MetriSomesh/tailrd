"use client";

import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Button } from "@/components/ui/button";
import {
  ApiRequestError,
  type EducationItem,
  type ExperienceItem,
  type ProfileBasics,
  type ProjectItem,
  type SkillCategoryItem,
  advanceStep,
  getProfile,
  parseResume,
  updateBasics,
  updateVoice,
  setEducations as apiSetEducations,
  setExperiences as apiSetExperiences,
  setProjects as apiSetProjects,
  setSkills as apiSetSkills,
} from "@/lib/api";
import { cn } from "@/lib/cn";
import { SITE } from "@/lib/site";
import { ArrowLeft, ArrowRight, Check, Plus, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const STEPS = ["Import", "Basics", "Education", "Experience", "Skills", "Projects", "Finish"] as const;

const inputCls =
  "w-full rounded-md border border-border-default bg-surface-sunken px-3.5 py-2.5 text-sm text-fg transition-colors placeholder:text-fg-tertiary focus:border-fg-primary focus:outline-none focus:ring-2 focus:ring-fg-primary/15";
const labelCls = "block font-mono text-2xs font-medium uppercase tracking-wide text-fg-secondary";

export function OnboardingWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [basics, setBasics] = useState<ProfileBasics>({ full_name: "" });
  const [educations, setEducations] = useState<EducationItem[]>([]);
  const [experiences, setExperiences] = useState<ExperienceItem[]>([]);
  const [skills, setSkills] = useState<SkillCategoryItem[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [hookLine, setHookLine] = useState("");
  const [allowAiProjects, setAllowAiProjects] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadNote, setUploadNote] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Load any existing profile so the wizard doubles as an editor and resumes.
  useEffect(() => {
    let cancelled = false;
    getProfile()
      .then((p) => {
        if (cancelled) return;
        setBasics({
          full_name: p.full_name ?? "",
          phone: p.phone ?? "",
          email: p.email ?? "",
          location: p.location ?? "",
          linkedin_url: p.linkedin_url ?? "",
          github_url: p.github_url ?? "",
        });
        setEducations(p.educations.map((e) => ({ degree: e.degree, institution: e.institution, dates: e.dates ?? "" })));
        setExperiences(
          p.experiences.map((e) => ({
            title: e.title, company: e.company, location: e.location ?? "",
            dates: e.dates ?? "", bullets: e.bullets ?? [],
          })),
        );
        setSkills(p.skills.map((s) => ({ category: s.category, items: s.items })));
        setProjects(
          p.projects.map((pr) => ({
            title: pr.title, description: pr.description ?? "",
            technologies: pr.technologies, url: pr.url ?? "",
          })),
        );
        setHookLine(p.hook_line ?? "");
        setAllowAiProjects(p.allow_ai_projects);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiRequestError && err.problem.status === 401) {
          router.replace("/login?next=/onboarding");
        } else {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function onUpload(file: File) {
    setUploading(true);
    setUploadNote(null);
    setError(null);
    try {
      const parsed = await parseResume(file);
      // Merge parsed values into any empty fields (never overwrite what's typed).
      setBasics((b) => ({
        full_name: b.full_name || parsed.full_name || "",
        phone: b.phone || parsed.phone || "",
        email: b.email || parsed.email || "",
        location: b.location ?? "",
        linkedin_url: b.linkedin_url ?? "",
        github_url: b.github_url ?? "",
      }));
      if (parsed.educations.length) setEducations((cur) => (cur.length ? cur : parsed.educations));
      if (parsed.experiences.length)
        setExperiences((cur) => (cur.length ? cur : parsed.experiences.map((e) => ({ ...e, bullets: e.bullets ?? [] }))));
      if (parsed.skills.length) setSkills((cur) => (cur.length ? cur : parsed.skills));
      if (parsed.projects.length) setProjects((cur) => (cur.length ? cur : parsed.projects));
      const found =
        [parsed.full_name, parsed.email].filter(Boolean).length +
        parsed.experiences.length + parsed.skills.length + parsed.educations.length;
      setUploadNote(
        found > 0
          ? "We prefilled what we could find. Review each step and fix anything."
          : "We couldn't extract much — fill the fields in manually.",
      );
    } catch (err) {
      setUploadNote(
        err instanceof ApiRequestError ? err.problem.detail : "Could not read that file. Try another.",
      );
    } finally {
      setUploading(false);
    }
  }

  // Persist the current step, returning true on success.
  async function saveCurrent(): Promise<boolean> {
    try {
      if (step === 1) {
        if (!basics.full_name.trim()) {
          setError("Your name is required.");
          return false;
        }
        await updateBasics({
          full_name: basics.full_name.trim(),
          phone: basics.phone || null,
          email: basics.email || null,
          location: basics.location || null,
          linkedin_url: basics.linkedin_url || null,
          github_url: basics.github_url || null,
        });
      } else if (step === 2) {
        await apiSetEducations(educations.filter((e) => e.degree.trim() && e.institution.trim()));
      } else if (step === 3) {
        await apiSetExperiences(
          experiences
            .filter((e) => e.title.trim() && e.company.trim())
            .map((e) => ({ ...e, bullets: e.bullets.filter((b) => b.trim()) })),
        );
      } else if (step === 4) {
        await apiSetSkills(
          skills
            .map((s) => ({ category: s.category.trim(), items: s.items.filter((i) => i.trim()) }))
            .filter((s) => s.category && s.items.length),
        );
      } else if (step === 5) {
        await apiSetProjects(projects.filter((p) => p.title.trim()));
      }
      return true;
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.problem.detail : "Could not save. Try again.");
      return false;
    }
  }

  async function next() {
    setError(null);
    setSaving(true);
    const ok = await saveCurrent();
    setSaving(false);
    if (ok) setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  async function finish() {
    setError(null);
    setSaving(true);
    try {
      await updateVoice({ hook_line: hookLine || null, allow_ai_projects: allowAiProjects });
      await advanceStep(8);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.problem.detail : "Could not finish. Try again.");
      setSaving(false);
    }
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="container-page flex h-16 items-center justify-between border-b border-border-subtle">
        <Link href="/" className="flex items-center gap-2.5">
          <span aria-hidden="true" className="size-3 rounded-[2px] bg-accent" />
          <span className="type-display text-lg tracking-tight text-fg">{SITE.name}</span>
        </Link>
        <ThemeToggle />
      </header>

      <main id="main" className="container-page flex flex-1 justify-center py-10">
        <div className="w-full max-w-2xl">
          {/* Progress */}
          <div className="flex items-center gap-1.5">
            {STEPS.map((label, i) => (
              <div key={label} className="flex flex-1 flex-col gap-1.5">
                <div className={cn("h-1 rounded-full", i <= step ? "bg-accent" : "bg-border-subtle")} />
                <span
                  className={cn(
                    "hidden font-mono text-2xs uppercase tracking-wide sm:block",
                    i === step ? "text-fg" : "text-fg-quaternary",
                  )}
                >
                  {label}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-8">
            {loading ? (
              <div className="grid min-h-[40vh] place-items-center">
                <span className="size-6 animate-spin rounded-full border-2 border-border-default border-t-accent" />
              </div>
            ) : (
              <>
                <p className="eyebrow flex items-center gap-2">
                  <span className="inline-block h-px w-6 bg-accent" />
                  Step {step + 1} of {STEPS.length}
                </p>

                {step === 0 && (
                  <ImportStep
                    uploading={uploading}
                    note={uploadNote}
                    onPick={() => fileRef.current?.click()}
                    fileRef={fileRef}
                    onFile={onUpload}
                  />
                )}
                {step === 1 && <BasicsStep basics={basics} setBasics={setBasics} />}
                {step === 2 && <EducationStep items={educations} setItems={setEducations} />}
                {step === 3 && <ExperienceStep items={experiences} setItems={setExperiences} />}
                {step === 4 && <SkillsStep items={skills} setItems={setSkills} />}
                {step === 5 && <ProjectsStep items={projects} setItems={setProjects} />}
                {step === 6 && (
                  <FinishStep
                    hookLine={hookLine}
                    setHookLine={setHookLine}
                    allowAi={allowAiProjects}
                    setAllowAi={setAllowAiProjects}
                  />
                )}

                {error && (
                  <div role="alert" className="mt-5 rounded-md border border-danger/40 bg-danger-subtle px-3.5 py-2.5 text-sm text-danger">
                    {error}
                  </div>
                )}

                {/* Nav */}
                <div className="mt-8 flex items-center justify-between gap-3 border-t border-border-subtle pt-6">
                  <Button
                    variant="ghost"
                    onClick={() => setStep((s) => Math.max(s - 1, 0))}
                    disabled={step === 0 || saving}
                  >
                    <ArrowLeft className="size-4" />
                    Back
                  </Button>

                  <div className="flex items-center gap-2">
                    {step === 0 && (
                      <Button variant="ghost" onClick={() => setStep(1)}>
                        Enter manually
                      </Button>
                    )}
                    {step < STEPS.length - 1 ? (
                      <Button onClick={next} loading={saving}>
                        {step === 0 ? "Continue" : "Save & continue"}
                        <ArrowRight className="size-4" />
                      </Button>
                    ) : (
                      <Button onClick={finish} loading={saving}>
                        <Check className="size-4" />
                        Finish setup
                      </Button>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Steps
// ---------------------------------------------------------------------------

function StepHead({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="mt-4">
      <h1 className="type-display text-2xl text-fg sm:text-3xl">{title}</h1>
      <p className="mt-2 text-sm text-fg-tertiary">{hint}</p>
    </div>
  );
}

function ImportStep({
  uploading, note, onPick, fileRef, onFile,
}: {
  uploading: boolean;
  note: string | null;
  onPick: () => void;
  fileRef: React.RefObject<HTMLInputElement | null>;
  onFile: (f: File) => void;
}) {
  return (
    <div>
      <StepHead
        title="Start from your resume"
        hint="Upload a PDF or DOCX and we'll prefill what we can. Or skip and enter everything by hand — you can always edit later."
      />
      <button
        type="button"
        onClick={onPick}
        disabled={uploading}
        className="mt-6 flex w-full flex-col items-center gap-3 rounded-md border border-dashed border-border-default bg-surface-raised px-6 py-12 text-center transition-colors hover:border-border-strong disabled:opacity-60"
      >
        <span className="grid size-11 place-items-center rounded-md border border-border-default text-fg">
          <Upload className="size-5" />
        </span>
        <span className="text-sm font-medium text-fg">
          {uploading ? "Reading your resume…" : "Upload resume (PDF or DOCX)"}
        </span>
        <span className="font-mono text-2xs uppercase tracking-wide text-fg-quaternary">Max 5 MB</span>
      </button>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
      {note && <p className="mt-4 text-sm text-fg-secondary">{note}</p>}
    </div>
  );
}

function BasicsStep({ basics, setBasics }: { basics: ProfileBasics; setBasics: (b: ProfileBasics) => void }) {
  const set = (k: keyof ProfileBasics, v: string) => setBasics({ ...basics, [k]: v });
  return (
    <div>
      <StepHead title="Your basics" hint="Contact details. These are copied verbatim onto every resume." />
      <div className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <label className={labelCls} htmlFor="fn">Full name</label>
          <input id="fn" className={inputCls} value={basics.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="Somesh Metri" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Text label="Email" v={basics.email ?? ""} on={(v) => set("email", v)} placeholder="you@example.com" />
          <Text label="Phone" v={basics.phone ?? ""} on={(v) => set("phone", v)} placeholder="9359611792" />
          <Text label="Location" v={basics.location ?? ""} on={(v) => set("location", v)} placeholder="Pune, India" />
          <Text label="LinkedIn URL" v={basics.linkedin_url ?? ""} on={(v) => set("linkedin_url", v)} placeholder="linkedin.com/in/…" />
          <Text label="GitHub URL" v={basics.github_url ?? ""} on={(v) => set("github_url", v)} placeholder="github.com/…" />
        </div>
      </div>
    </div>
  );
}

function EducationStep({ items, setItems }: { items: EducationItem[]; setItems: (v: EducationItem[]) => void }) {
  const upd = (i: number, k: keyof EducationItem, v: string) =>
    setItems(items.map((it, idx) => (idx === i ? { ...it, [k]: v } : it)));
  return (
    <div>
      <StepHead title="Education" hint="Degrees and institutions. Kept exactly as entered." />
      <div className="mt-6 space-y-4">
        {items.map((it, i) => (
          <Card key={i} onRemove={() => setItems(items.filter((_, idx) => idx !== i))}>
            <Text label="Degree" v={it.degree} on={(v) => upd(i, "degree", v)} placeholder="B.E. Computer Science" />
            <Text label="Institution" v={it.institution} on={(v) => upd(i, "institution", v)} placeholder="University name" />
            <Text label="Dates" v={it.dates ?? ""} on={(v) => upd(i, "dates", v)} placeholder="2021 - 2025" />
          </Card>
        ))}
      </div>
      <AddButton label="Add education" onClick={() => setItems([...items, { degree: "", institution: "", dates: "" }])} />
    </div>
  );
}

function ExperienceStep({ items, setItems }: { items: ExperienceItem[]; setItems: (v: ExperienceItem[]) => void }) {
  const upd = (i: number, patch: Partial<ExperienceItem>) =>
    setItems(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  return (
    <div>
      <StepHead title="Experience" hint="Roles and achievements. We rephrase these per job — never invent them. One bullet per line." />
      <div className="mt-6 space-y-4">
        {items.map((it, i) => (
          <Card key={i} onRemove={() => setItems(items.filter((_, idx) => idx !== i))}>
            <div className="grid gap-3 sm:grid-cols-2">
              <Text label="Title" v={it.title} on={(v) => upd(i, { title: v })} placeholder="Software Engineer" />
              <Text label="Company" v={it.company} on={(v) => upd(i, { company: v })} placeholder="Acme" />
              <Text label="Location" v={it.location ?? ""} on={(v) => upd(i, { location: v })} placeholder="Remote" />
              <Text label="Dates" v={it.dates ?? ""} on={(v) => upd(i, { dates: v })} placeholder="2023 - Present" />
            </div>
            <div className="space-y-1.5">
              <label className={labelCls}>Achievements (one per line)</label>
              <textarea
                rows={4}
                className={cn(inputCls, "resize-y")}
                value={it.bullets.join("\n")}
                onChange={(e) => upd(i, { bullets: e.target.value.split("\n") })}
                placeholder={"Built X that improved Y by Z%\nLed migration to …"}
              />
            </div>
          </Card>
        ))}
      </div>
      <AddButton
        label="Add experience"
        onClick={() => setItems([...items, { title: "", company: "", location: "", dates: "", bullets: [] }])}
      />
    </div>
  );
}

function SkillsStep({ items, setItems }: { items: SkillCategoryItem[]; setItems: (v: SkillCategoryItem[]) => void }) {
  return (
    <div>
      <StepHead title="Skills" hint="Group your skills into categories. Separate items with commas." />
      <div className="mt-6 space-y-4">
        {items.map((it, i) => (
          <Card key={i} onRemove={() => setItems(items.filter((_, idx) => idx !== i))}>
            <Text
              label="Category"
              v={it.category}
              on={(v) => setItems(items.map((x, idx) => (idx === i ? { ...x, category: v } : x)))}
              placeholder="Languages"
            />
            <Text
              label="Items (comma separated)"
              v={it.items.join(", ")}
              on={(v) => setItems(items.map((x, idx) => (idx === i ? { ...x, items: v.split(",").map((s) => s.trim()) } : x)))}
              placeholder="Python, TypeScript, SQL"
            />
          </Card>
        ))}
      </div>
      <AddButton label="Add category" onClick={() => setItems([...items, { category: "", items: [] }])} />
    </div>
  );
}

function ProjectsStep({ items, setItems }: { items: ProjectItem[]; setItems: (v: ProjectItem[]) => void }) {
  const upd = (i: number, patch: Partial<ProjectItem>) =>
    setItems(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  return (
    <div>
      <StepHead title="Projects" hint="Optional. Notable work with the tech used and its impact." />
      <div className="mt-6 space-y-4">
        {items.map((it, i) => (
          <Card key={i} onRemove={() => setItems(items.filter((_, idx) => idx !== i))}>
            <Text label="Title" v={it.title} on={(v) => upd(i, { title: v })} placeholder="Project name" />
            <div className="space-y-1.5">
              <label className={labelCls}>Description</label>
              <textarea rows={3} className={cn(inputCls, "resize-y")} value={it.description ?? ""} onChange={(e) => upd(i, { description: e.target.value })} placeholder="What it does and the impact." />
            </div>
            <Text label="Technologies (comma separated)" v={it.technologies.join(", ")} on={(v) => upd(i, { technologies: v.split(",").map((s) => s.trim()) })} placeholder="Next.js, FastAPI, Postgres" />
            <Text label="URL" v={it.url ?? ""} on={(v) => upd(i, { url: v })} placeholder="https://…" />
          </Card>
        ))}
      </div>
      <AddButton label="Add project" onClick={() => setItems([...items, { title: "", description: "", technologies: [], url: "" }])} />
    </div>
  );
}

function FinishStep({
  hookLine, setHookLine, allowAi, setAllowAi,
}: {
  hookLine: string;
  setHookLine: (v: string) => void;
  allowAi: boolean;
  setAllowAi: (v: boolean) => void;
}) {
  return (
    <div>
      <StepHead title="Your voice" hint="A hook line opens every tailored summary. And decide whether the AI may draft brand-new projects." />
      <div className="mt-6 space-y-5">
        <div className="space-y-1.5">
          <label className={labelCls} htmlFor="hook">Hook line</label>
          <textarea id="hook" rows={3} className={cn(inputCls, "resize-y")} value={hookLine} onChange={(e) => setHookLine(e.target.value)} placeholder="Skilled at turning ambiguous problems into reliable systems that ship." />
        </div>
        <label className="flex items-start gap-3 rounded-md border border-border-default bg-surface-raised p-4">
          <input type="checkbox" checked={allowAi} onChange={(e) => setAllowAi(e.target.checked)} className="mt-0.5 size-4 accent-[var(--accent)]" />
          <span>
            <span className="block text-sm font-medium text-fg">Allow AI to draft new projects</span>
            <span className="mt-0.5 block text-xs text-fg-tertiary">When on, tailoring may invent relevant projects. Off keeps only projects you entered.</span>
          </span>
        </label>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small shared bits
// ---------------------------------------------------------------------------

function Text({ label, v, on, placeholder }: { label: string; v: string; on: (v: string) => void; placeholder?: string }) {
  return (
    <div className="space-y-1.5">
      <label className={labelCls}>{label}</label>
      <input className={inputCls} value={v} onChange={(e) => on(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function Card({ children, onRemove }: { children: React.ReactNode; onRemove: () => void }) {
  return (
    <div className="relative space-y-3 rounded-md border border-border-default bg-surface-raised p-4">
      <button
        type="button"
        onClick={onRemove}
        aria-label="Remove"
        className="absolute right-3 top-3 grid size-7 place-items-center rounded-md text-fg-quaternary transition-colors hover:bg-surface-sunken hover:text-danger"
      >
        <Trash2 className="size-3.5" />
      </button>
      {children}
    </div>
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mt-4 flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-border-default py-3 font-mono text-2xs uppercase tracking-wide text-fg-tertiary transition-colors hover:border-border-strong hover:text-fg"
    >
      <Plus className="size-3.5" />
      {label}
    </button>
  );
}
