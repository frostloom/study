import AppKit
let output = CommandLine.arguments[1]
try FileManager.default.createDirectory(atPath: output, withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: pixels * 4, bitsPerPixel: 32)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        let s = CGFloat(pixels)
        NSColor.white.setFill()
        NSBezierPath(roundedRect: NSRect(x: s*0.04, y: s*0.04, width: s*0.92, height: s*0.92), xRadius: s*0.2, yRadius: s*0.2).fill()
        NSColor.black.setStroke()
        let book = NSBezierPath()
        book.lineWidth = max(1.5, s*0.045)
        book.lineJoinStyle = .round
        book.move(to: NSPoint(x:s*0.5,y:s*0.24))
        book.curve(to:NSPoint(x:s*0.19,y:s*0.29), controlPoint1:NSPoint(x:s*0.38,y:s*0.31), controlPoint2:NSPoint(x:s*0.29,y:s*0.32))
        book.line(to:NSPoint(x:s*0.19,y:s*0.73))
        book.curve(to:NSPoint(x:s*0.5,y:s*0.69), controlPoint1:NSPoint(x:s*0.3,y:s*0.76), controlPoint2:NSPoint(x:s*0.4,y:s*0.75))
        book.curve(to:NSPoint(x:s*0.81,y:s*0.73), controlPoint1:NSPoint(x:s*0.6,y:s*0.75), controlPoint2:NSPoint(x:s*0.7,y:s*0.76))
        book.line(to:NSPoint(x:s*0.81,y:s*0.29))
        book.curve(to:NSPoint(x:s*0.5,y:s*0.24), controlPoint1:NSPoint(x:s*0.71,y:s*0.32), controlPoint2:NSPoint(x:s*0.62,y:s*0.31))
        book.line(to:NSPoint(x:s*0.5,y:s*0.69))
        book.stroke()
        NSGraphicsContext.restoreGraphicsState()
        let png = bitmap.representation(using: .png, properties: [:])!
        let suffix = scale == 2 ? "@2x" : ""
        try png.write(to: URL(fileURLWithPath: "\(output)/icon_\(size)x\(size)\(suffix).png"))
    }
}
