$code = @"
using System;
using System.Threading.Tasks;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage;
using Windows.Storage.Streams;

public static class OcrHelper {
  public static async Task<string> Read(string path) {
    var file = await StorageFile.GetFileFromPathAsync(path);
    var stream = await file.OpenAsync(FileAccessMode.Read);
    var decoder = await BitmapDecoder.CreateAsync(stream);
    var bitmap = await decoder.GetSoftwareBitmapAsync();
    var engine = OcrEngine.TryCreateFromUserProfileLanguages();
    if (engine == null) return "NULL";
    var result = await engine.RecognizeAsync(bitmap);
    return result.Text;
  }
}
"@
Add-Type -TypeDefinition $code -Language CSharp -ReferencedAssemblies @(
  'System.Runtime.WindowsRuntime',
  "$env:windir\System32\WinMetadata\Windows.Foundation.winmd",
  "$env:windir\System32\WinMetadata\Windows.Media.winmd",
  "$env:windir\System32\WinMetadata\Windows.Storage.winmd",
  "$env:windir\System32\WinMetadata\Windows.Graphics.winmd"
)
$text = [OcrHelper]::Read('C:\Users\Admin\Documents\Codex\Exam\backend\media\2232bfd3-8cfd-4c85-9d16-883ff02322a5\f2426f82-437b-4554-9f75-9e59a76ce5c0\image12.png').GetAwaiter().GetResult()
Write-Output $text
