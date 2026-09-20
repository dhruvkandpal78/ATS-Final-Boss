import React from 'react';
import { Button } from './components/ui/Button';
import { Input } from './components/ui/Input';
import { Card, CardHeader, CardTitle } from './components/ui/Card';
import { Badge } from './components/ui/Badge';

export default function Gallery() {
  return (
    <div className="container py-12 space-y-12">
      <h1 className="h1">Component Gallery</h1>
      
      <section className="space-y-6">
        <h2 className="h2">Buttons</h2>
        <div className="flex flex-wrap gap-4 items-center">
          <Button variant="primary">Primary</Button>
          <Button variant="primary" isLoading>Loading</Button>
          <Button variant="primary" disabled>Disabled</Button>
          
          <Button variant="secondary">Secondary</Button>
          <Button variant="secondary" disabled>Disabled</Button>

          <Button variant="tertiary">Tertiary</Button>
        </div>
      </section>
      
      <section className="space-y-6">
        <h2 className="h2">Inputs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-2xl">
          <Input label="Normal Input" placeholder="Enter text..." />
          <Input label="With Help Text" helpText="This is some helpful text" />
          <Input label="Error State" error="This field is required" defaultValue="Invalid value" />
          <Input label="Disabled" disabled value="Cannot edit me" />
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="h2">Cards & Badges</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card>
            <CardHeader>
              <CardTitle>Standard Card</CardTitle>
            </CardHeader>
            <p className="body text-[--muted]">
              This is a standard card with body text. It uses the default shadow and padding.
            </p>
            <div className="mt-4 flex gap-2">
              <Badge variant="success">Passed</Badge>
              <Badge variant="danger">Failed</Badge>
            </div>
          </Card>
          
          <Card className="shadow-float">
            <CardHeader>
              <CardTitle>Floating Card</CardTitle>
            </CardHeader>
            <p className="body text-[--muted]">
              This card uses the shadow-float token for emphasis.
            </p>
            <div className="mt-4 flex gap-2">
              <Badge variant="warning">Warning</Badge>
              <Badge variant="neutral">Pending</Badge>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}
