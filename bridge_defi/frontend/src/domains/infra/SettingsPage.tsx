import { useEffect, useState, type FormEvent } from 'react';

type Settings = {
  theme: 'dark' | 'light';
  language: string;
};

const DEFAULT_SETTINGS: Settings = {
  theme: 'dark',
  language: 'en',
};

export function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSaved(false);
  }, [settings]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaved(true);
  }

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <p>Persisted UI preferences and account defaults.</p>

      <form className="card" onSubmit={handleSubmit}>
        <label className="form-group">
          <span>Theme</span>
          <select
            value={settings.theme}
            onChange={(event) =>
              setSettings((current) => ({
                ...current,
                theme: event.target.value === 'light' ? 'light' : 'dark',
              }))
            }
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>

        <label className="form-group">
          <span>Language</span>
          <input
            type="text"
            value={settings.language}
            onChange={(event) =>
              setSettings((current) => ({
                ...current,
                language: event.target.value,
              }))
            }
          />
        </label>

        <button className="btn-primary" type="submit">
          Save Settings
        </button>

        {saved && (
          <p role="status" className="success-text">
            Settings saved.
          </p>
        )}
      </form>
    </div>
  );
}
