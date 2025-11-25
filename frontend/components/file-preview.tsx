import { FileIcon, X } from "lucide-react"

interface FilePreviewProps {
  file: File
  onRemove: () => void
}

export function FilePreview({ file, onRemove }: FilePreviewProps) {
  return (
    <div className="flex items-center gap-2 bg-[#1F1F1F] border border-[#333333] rounded-lg p-2 hover:bg-[#2F2F2F] transition-colors group">
      <div className="w-10 h-10 bg-[#00FF9D] rounded-lg flex items-center justify-center shrink-0">
        <FileIcon className="w-5 h-5 text-black" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate text-white">{file.name}</p>
        <p className="text-xs text-[#666666]">PDF</p>
      </div>
      <button
        type="button"
        className="h-8 w-8 flex items-center justify-center text-[#666666] hover:text-red-400 hover:bg-red-900/30 rounded transition-colors opacity-0 group-hover:opacity-100"
        onClick={onRemove}
        aria-label={`Remove ${file.name}`}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}
