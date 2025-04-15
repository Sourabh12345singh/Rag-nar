
import React, { useState, useCallback, useEffect } from 'react';
import { Upload, Send, FileText, Sparkles, Loader2 } from 'lucide-react';
import { uploadPDFs, processPDFs, queryDocuments, clearBooks } from './api';

interface Chunk {
  source: string;
  score: number;
  text: string;
}

function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState('');

  // Clear books folder on page load/refresh
  useEffect(() => {
    const clearFolder = async () => {
      try {
        const result = await clearBooks();
        setStatus(result.message);
      } catch (error) {
        setStatus('Failed to clear books folder');
        console.error(error);
      }
    };
    clearFolder();
  }, []); // Empty dependency array ensures this runs once on mount

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) {
      setStatus('Please select at least one PDF file.');
      return;
    }
    setIsLoading(true);
    try {
      const result = await uploadPDFs(files);
      setStatus(`Uploaded ${result.files_uploaded} files successfully.`);
    } catch (error: any) {
      setStatus(error.message || 'Error uploading files.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProcess = async () => {
    setIsLoading(true);
    try {
      const result = await processPDFs();
      setStatus(`Processed ${result.books} books with ${result.chunks} chunks.`);
    } catch (error: any) {
      setStatus(error.message || 'Error processing PDFs.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt) {
      setStatus('Please enter a query.');
      return;
    }
    setIsLoading(true);
    try {
      const { chunks, gemini_response } = await queryDocuments(prompt);
      setChunks(chunks);
      setResponse(gemini_response);
      setStatus('');
    } catch (error: any) {
      setStatus(error.message || 'Error processing query.');
      setChunks([]);
      setResponse('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 relative overflow-hidden">
      {/* Animated stars background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(50)].map((_, i) => (
          <div
            key={i}
            className="animate-falling-star"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 5}s`,
              animationDuration: `${Math.random() * 3 + 2}s`,
            }}
          />
        ))}
      </div>

      {/* Header */}
      <header className="border-b border-gray-800 relative z-10 bg-opacity-90 bg-gray-900 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center space-x-3">
            <Sparkles className="w-10 h-10 text-purple-400" />
            <h1 className="text-4xl font-bold font-display">
              <span className="bg-gradient-to-r from-purple-400 via-pink-500 to-purple-600 bg-clip-text text-transparent">
                RAGnar
              </span>
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 relative z-10">
        <div className="max-w-3xl mx-auto">
          {/* Status Message */}
          {status && (
            <div className="mb-4 p-4 bg-gray-800/50 rounded-xl text-gray-300">
              {status}
            </div>
          )}

          {/* Query Section */}
          <div className="mb-8">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="relative group">
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ask me anything... (Add PDFs below for context-specific answers)"
                  className="w-full bg-gray-800/50 backdrop-blur-sm rounded-xl px-6 py-4 text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none border border-gray-700 shadow-lg transition-all duration-300 group-hover:border-purple-500/50"
                  rows={4}
                />
                <button
                  type="submit"
                  disabled={isLoading || !prompt}
                  className="absolute bottom-4 right-4 bg-purple-500 text-white rounded-lg px-4 py-2 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-all duration-300"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Thinking...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      <span>Ask</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Upload Section */}
          <div className="bg-gray-800/30 backdrop-blur-sm rounded-xl p-6 border border-gray-700 transition-all duration-300 hover:border-purple-500/30">
            <div className="border-2 border-dashed border-gray-600 rounded-xl p-8 text-center transition-all duration-300 hover:border-purple-500/50">
              <input
                type="file"
                id="file-upload"
                className="hidden"
                onChange={handleFileChange}
                multiple
                accept=".pdf"
              />
              <label
                htmlFor="file-upload"
                className="cursor-pointer flex flex-col items-center"
              >
                <Upload className="w-12 h-12 text-purple-400 mb-4" />
                <span className="text-lg font-medium mb-2">Add PDF context (optional)</span>
                <span className="text-sm text-gray-400">Drop files here or click to browse</span>
              </label>
            </div>
            {files.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-gray-300 mb-2">Context Files:</h3>
                <div className="space-y-2">
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-2 text-sm text-gray-400 bg-gray-800/50 rounded-lg px-3 py-2"
                    >
                      <FileText className="w-4 h-4 text-purple-400" />
                      <span>{file.name}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex space-x-4">
                  <button
                    onClick={handleUpload}
                    disabled={isLoading || files.length === 0}
                    className="bg-purple-500 text-white rounded-lg px-4 py-2 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    <Upload className="w-5 h-5" />
                    <span>Upload PDFs</span>
                  </button>
                  <button
                    onClick={handleProcess}
                    disabled={isLoading}
                    className="bg-green-500 text-white rounded-lg px-4 py-2 hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                  >
                    <FileText className="w-5 h-5" />
                    <span>Process PDFs</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Response Section */}
          {(chunks.length > 0 || response) && (
            <div className="mt-8 bg-gray-800/30 backdrop-blur-sm rounded-xl p-6 border border-gray-700">
              {chunks.length > 0 && (
                <>
                  <div className="flex items-center space-x-3 mb-4">
                    <FileText className="w-6 h-6 text-purple-400" />
                    <h3 className="text-lg font-medium">Top Similar Chunks</h3>
                  </div>
                  <div className="space-y-4 mb-6">
                    {chunks.map((chunk, index) => (
                      <div
                        key={index}
                        className="bg-gray-800/50 p-4 rounded-lg border border-gray-700"
                      >
                        <p>
                          <strong>{index + 1}. Source:</strong> {chunk.source}
                        </p>
                        <p>
                          <strong>Score:</strong> {chunk.score.toFixed(4)}
                        </p>
                        <p>
                          <strong>Text:</strong> {chunk.text.substring(0, 200)}...
                        </p>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {response && (
                <>
                  <div className="flex items-center space-x-3 mb-4">
                    <Sparkles className="w-6 h-6 text-purple-400" />
                    <h3 className="text-lg font-medium">Response</h3>
                  </div>
                  <p className="text-gray-300 leading-relaxed">{response}</p>
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
